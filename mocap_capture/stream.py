"""STREAM source: a tablet running mocap-camera-app, over stream protocol v1.

The spec is `docs/stream-protocol-v1.md` in mocap-contracts and the
parsing comes from its reference reader, `mocap_contracts.stream_v1`.

    prepare()   checks the camera serves a v1 stream, then syncs clocks
    start()     opens a fresh connection (so the file starts at a key frame)
                and writes the H.264 unchanged into raw/<role>.mkv through
                FFmpeg (`-c copy`); returns once the first frame is in
    stop()      closes the stream, then syncs clocks again
    collect()   writes raw/<role>.timestamps.csv: every timed frame on the
                host clock, the offset interpolated between the two syncs

The host clock is Unix time in ns (`time.time_ns`, CLOCK_REALTIME), the
clock the spec names and the one UVC cameras are stamped with.

Nothing is guessed. A frame without a v1 timestamp gets no row, a jump in
the SEI sequence is a gap, and a dropped connection is reconnected and
reported. All of these go to `problems`, so a gap stays visible.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mocap_contracts import CameraConfig, layout, stream_v1
from mocap_contracts import CameraSource as SourceKind

from mocap_capture.sources import register

log = logging.getLogger(__name__)

Clock = Callable[[], int]


class StreamSourceError(RuntimeError):
    """A STREAM camera that can't be used for the take."""


# ---------------------------------------------------------------- NAL splitting

class NalSplitter:
    """Cut an Annex-B byte stream, fed in arbitrary chunks, into whole NAL units.

    `feed` returns the bytes that are now complete, exactly as received, plus
    the (nal_unit_type, nal) pairs in them. The last NAL unit is held back until
    the next start code shows it is complete. `reset` drops it, as after a
    dropped connection, where it may be truncated.
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
        self._buf += chunk
        last = self._buf.rfind(b"\x00\x00\x01")
        if last <= 0:
            return b"", []
        cut = last - 1 if self._buf[last - 1] == 0 else last
        done = bytes(self._buf[:cut])
        del self._buf[:cut]
        return done, list(stream_v1.nal_units(done))

    def reset(self) -> None:
        self._buf.clear()


# ---------------------------------------------------------------- frames

@dataclass(frozen=True)
class ReceivedFrame:
    index: int  # position in the recorded file
    timestamp: stream_v1.Timestamp | None
    recv_ns: int  # host clock when its slice arrived


class FrameTracker:
    """Number frames as `stream_v1.frames` does, one NAL unit at a time.

    A frame counts when its slice arrives, so a timestamp SEI whose slice was
    lost to a dropped connection never becomes a row.
    """

    def __init__(self) -> None:
        self.frames: list[ReceivedFrame] = []
        self.problems: list[str] = []
        self._pending: stream_v1.Timestamp | str | None = None

    def add(self, nal_type: int, nal: bytes, recv_ns: int) -> None:
        if nal_type == stream_v1.NAL_SEI:
            try:
                ts = stream_v1.parse_timestamp_sei(nal)
            except stream_v1.StreamError as e:
                self._pending = str(e)
                return
            if ts is not None:
                self._pending = ts
        elif nal_type in (stream_v1.NAL_IDR, stream_v1.NAL_SLICE):
            pending, self._pending = self._pending, None
            index = len(self.frames)
            if isinstance(pending, stream_v1.Timestamp):
                self.frames.append(ReceivedFrame(index, pending, recv_ns))
                return
            reason = pending or "slice without a v1 timestamp SEI"
            self.problems.append(f"frame {index}: untimed ({reason})")
            self.frames.append(ReceivedFrame(index, None, recv_ns))

    def drop_pending(self) -> None:
        self._pending = None

    @property
    def timed(self) -> list[ReceivedFrame]:
        return [f for f in self.frames if f.timestamp is not None]


# ---------------------------------------------------------------- clock sync

@dataclass(frozen=True)
class SyncPoint:
    """One sync: the sensor clock at `host_ns`, and host minus sensor."""

    host_ns: int
    sensor_ns: int
    offset_ns: int


def sync_clock(
    host: str,
    port: int,
    *,
    probes: int = 200,
    interval_s: float = 0.01,
    timeout_s: float = 0.2,
    clock: Clock = time.time_ns,
) -> SyncPoint:
    """Probe the camera's sync port and return the offset, per spec §4–§5."""
    answered: list[stream_v1.Probe] = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout_s)
        for token in range(probes):
            t_send = clock()
            try:
                sock.sendto(stream_v1.sync_request(token), (host, port))
                while True:
                    data = sock.recv(64)
                    t_recv = clock()
                    got, sensor_ns, _ = stream_v1.parse_sync_reply(data)
                    if got == token:  # anything else is a late reply to an older probe
                        answered.append(stream_v1.Probe(t_send, t_recv, sensor_ns))
                        break
            except (TimeoutError, stream_v1.StreamError):
                pass
            except OSError as e:
                raise StreamSourceError(f"clock sync with {host}:{port}: {e}") from None
            time.sleep(interval_s)
    try:
        offset = stream_v1.sync_offset(answered)
    except stream_v1.StreamError as e:
        raise StreamSourceError(f"clock sync with {host}:{port}: {e}") from None
    now = clock()
    return SyncPoint(host_ns=now, sensor_ns=now - offset, offset_ns=offset)


def host_timestamps(
    frames: list[ReceivedFrame], before: SyncPoint, after: SyncPoint
) -> list[tuple[int, int]]:
    """(frame index, host_ts_ns) for every timed frame."""
    b = (before.sensor_ns, before.offset_ns)
    a = (after.sensor_ns, after.offset_ns)
    return [
        (f.index, stream_v1.host_ts_ns(f.timestamp.sensor_ns, b, a))
        for f in frames
        if f.timestamp is not None
    ]


# ---------------------------------------------------------------- video

def open_video(host: str, port: int, timeout_s: float) -> tuple[socket.socket, bytes]:
    """GET /h264.raw (spec §2); returns the socket and any body bytes already read."""
    sock = socket.create_connection((host, port), timeout=timeout_s)
    try:
        sock.sendall(b"GET /h264.raw HTTP/1.0\r\n\r\n")
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(4096)
            if not chunk:
                raise StreamSourceError(f"{host}:{port} closed before the HTTP header ended")
            head += chunk
            if len(head) > 16384:
                raise StreamSourceError(f"{host}:{port}: HTTP header too long")
        head, body = head.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n", 1)[0].decode("latin-1")
        if status.split()[1:2] != ["200"]:
            raise StreamSourceError(f"{host}:{port}: {status}")
        return sock, body
    except BaseException:
        sock.close()
        raise


class Muxer(Protocol):
    def write(self, data: bytes) -> None: ...

    def close(self) -> None: ...


ERROR_LINES = 5  # of FFmpeg's stderr kept in an error, its last ones


class FfmpegMuxer:
    """Raw H.264 on stdin → MKV, stream copied, never re-encoded.

    The MKV's own timing is FFmpeg's (constant `fps`); the real timing is the
    timestamps file.
    """

    def __init__(self, out: Path, fps: float):
        self._out = out
        self._err = tempfile.TemporaryFile()
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
            "-f", "h264", "-framerate", f"{fps:g}", "-i", "pipe:0",
            "-c", "copy", "-y", str(out),
        ]
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self._err)

    def write(self, data: bytes) -> None:
        self._proc.stdin.write(data)

    def close(self) -> None:
        self._proc.stdin.close()
        code = self._proc.wait()
        self._err.seek(0)
        lines = self._err.read().decode(errors="replace").strip().splitlines()
        self._err.close()
        if code != 0:
            tail = "\n".join(lines[-ERROR_LINES:])
            raise StreamSourceError(f"ffmpeg writing {self._out} exited {code}:\n{tail}")


# ---------------------------------------------------------------- the source

@register(SourceKind.Value("CAMERA_SOURCE_STREAM"))
class StreamSource:
    def __init__(
        self,
        config: CameraConfig,
        *,
        sync_probes: int = 200,
        sync_interval_s: float = 0.01,
        timeout_s: float = 5.0,
        reconnect_delay_s: float = 0.5,
        muxer: Callable[[Path, float], Muxer] = FfmpegMuxer,
        clock: Clock = time.time_ns,
    ):
        self.config = config
        self.problems: list[str] = []
        self._sync = dict(probes=sync_probes, interval_s=sync_interval_s, clock=clock)
        self._timeout_s = timeout_s
        self._reconnect_delay_s = reconnect_delay_s
        self._make_muxer = muxer
        self._clock = clock
        self._before: SyncPoint | None = None
        self._after: SyncPoint | None = None
        self._tracker = FrameTracker()
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()
        self._first_frame = threading.Event()
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._error: BaseException | None = None

    @property
    def _where(self) -> str:
        return f"role {self.config.role} ({self.config.stream_host}:{self.config.video_port})"

    def prepare(self) -> None:
        self._check_v1()
        self._before = self._sync_clock()

    def start(self, take_dir: Path) -> None:
        if self._before is None:
            raise StreamSourceError(f"{self._where}: start() before prepare()")
        out = layout.raw_video(take_dir, self.config.role)
        out.parent.mkdir(parents=True, exist_ok=True)
        self._mux = self._make_muxer(out, self.config.fps)
        self._thread = threading.Thread(target=self._record, name=f"stream-{self.config.role}")
        self._thread.start()
        if not self._first_frame.wait(self._timeout_s):
            self.stop()
            raise StreamSourceError(f"{self._where}: no frame within {self._timeout_s:g}s of start")

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stopping.set()
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # already closed by the camera
        self._thread.join()
        self._thread = None
        self._mux.close()
        if self._error is not None:
            raise StreamSourceError(f"{self._where}: recording failed: {self._error}")
        self._after = self._sync_clock()

    def collect(self, take_dir: Path) -> list[Path]:
        if self._before is None or self._after is None:
            raise StreamSourceError(f"{self._where}: collect() needs both clock syncs")
        self.problems.extend(self._tracker.problems)
        timed = self._tracker.timed
        for a, b in stream_v1.seq_gaps([f.timestamp for f in timed]):
            self._problem(f"gap: seq {a} → {b}, {b - a - 1} frame(s) missing")
        rows = host_timestamps(timed, self._before, self._after)
        for (index, ts), frame in zip(rows, timed):
            if ts > frame.recv_ns:
                self._problem(f"frame {index}: host time {ts} is after it arrived ({frame.recv_ns})")
        path = layout.raw_timestamps(take_dir, self.config.role)
        lines = [",".join(layout.TIMESTAMPS_COLUMNS)] + [f"{i},{ts}" for i, ts in rows]
        path.write_text("\n".join(lines) + "\n")
        return [layout.raw_video(take_dir, self.config.role), path]

    # -------------------------------------------------------------- internals

    def _sync_clock(self) -> SyncPoint:
        return sync_clock(self.config.stream_host, self.config.sync_port, **self._sync)

    def _check_v1(self) -> None:
        """Read until the first timed frame, so a non-v1 camera fails before the take."""
        sock, body = self._connect()
        try:
            splitter, tracker = NalSplitter(), FrameTracker()
            deadline = time.monotonic() + self._timeout_s
            chunk = body
            while not tracker.timed:
                for nal_type, nal in splitter.feed(chunk)[1]:
                    tracker.add(nal_type, nal, 0)
                left = deadline - time.monotonic()
                if tracker.timed or left <= 0:
                    break
                sock.settimeout(left)
                try:
                    chunk = sock.recv(65536)
                except TimeoutError:
                    break
                if not chunk:
                    break
        except OSError as e:
            raise StreamSourceError(f"{self._where}: {e}") from None
        finally:
            sock.close()
        if not tracker.timed:
            raise StreamSourceError(f"{self._where}: no frame with a v1 timestamp SEI")

    def _connect(self) -> tuple[socket.socket, bytes]:
        try:
            return open_video(self.config.stream_host, self.config.video_port, self._timeout_s)
        except OSError as e:
            raise StreamSourceError(f"{self._where}: {e}") from None

    def _record(self) -> None:
        splitter = NalSplitter()
        connected_once = False
        try:
            while not self._stopping.is_set():
                try:
                    sock, body = self._connect()
                except StreamSourceError as e:
                    self._problem(f"reconnect failed: {e}")
                    self._stopping.wait(self._reconnect_delay_s)
                    continue
                if connected_once:
                    self._problem(f"reconnected after {len(self._tracker.frames)} frame(s)")
                connected_once = True
                with self._lock:
                    self._sock = sock
                try:
                    self._read(sock, body, splitter)
                finally:
                    with self._lock:
                        self._sock = None
                    sock.close()
                if not self._stopping.is_set():
                    timed = self._tracker.timed
                    last = timed[-1].timestamp.seq if timed else None
                    self._problem(f"connection lost after seq {last}")
                splitter.reset()
                self._tracker.drop_pending()
        except BaseException as e:  # reported by stop()
            self._error = e
            self._first_frame.set()

    def _read(self, sock: socket.socket, chunk: bytes, splitter: NalSplitter) -> None:
        sock.settimeout(None)
        while True:
            done, nals = splitter.feed(chunk)
            if done:
                self._mux.write(done)
                now = self._clock()
                for nal_type, nal in nals:
                    self._tracker.add(nal_type, nal, now)
                if self._tracker.frames:
                    self._first_frame.set()
            try:
                chunk = sock.recv(65536)
            except OSError:
                return
            if not chunk:
                return

    def _problem(self, text: str) -> None:
        log.warning("%s: %s", self._where, text)
        self.problems.append(text)
