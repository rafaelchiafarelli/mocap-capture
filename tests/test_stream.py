import csv
import random
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
from mocap_contracts import CameraConfig, layout, stream_v1
from mocap_contracts import CameraSource as SourceKind

from mocap_capture.sources import CameraSource, create_source
from mocap_capture.stream import (
    FrameTracker,
    NalSplitter,
    ReceivedFrame,
    StreamSource,
    StreamSourceError,
    SyncPoint,
    host_timestamps,
    sync_clock,
)

FIXTURES = Path(__file__).parents[1] / "third_party" / "mocap-contracts" / "fixtures" / "stream-v1"
STREAM = SourceKind.Value("CAMERA_SOURCE_STREAM")

SPS = b"\x00\x00\x00\x01\x67\x42\x00\x1f\xaa"
PPS = b"\x00\x00\x00\x01\x68\xce\x3c\x80"
IDR = b"\x00\x00\x00\x01\x65\x88\x84\x21"
SLICE = b"\x00\x00\x00\x01\x41\x9a\x02\x04"
AUD = b"\x00\x00\x00\x01\x09\xf0"  # ends the last slice, so it counts as complete

if not FIXTURES.is_dir():
    pytest.skip("run `git submodule update --init` for the stream v1 fixtures", allow_module_level=True)


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_rows(name: str) -> list[dict]:
    with open(FIXTURES / name) as f:
        return list(csv.DictReader(f))


def synthetic(seqs, sensor_ns) -> bytes:
    """SPS, PPS, then one SEI + slice per seq; the first slice is a key frame."""
    out = SPS + PPS
    for i, seq in enumerate(seqs):
        s = sensor_ns(seq)
        out += stream_v1.build_timestamp_sei(seq, s, s) + (IDR if i == 0 else SLICE)
    return out


class FakeCamera:
    """mocap-camera-app as stream protocol v1 sees it.

    Connection n gets `sessions[n]` (the last one repeats). A session either
    closes after its bytes (a dropped connection) or stays open until the
    test ends. The sync port answers on a sensor clock of
    `(host - host0) * (1 + drift) + sensor0`.
    """

    def __init__(self, sessions, *, sensor0=0, drift=0.0):
        self.sessions = sessions
        self.host0 = time.time_ns()
        self.sensor0 = sensor0
        self.drift = drift
        self.connections = 0
        self._open: list[socket.socket] = []
        self._tcp = socket.create_server(("127.0.0.1", 0))
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp.bind(("127.0.0.1", 0))
        self._done = threading.Event()
        for target in (self._serve_video, self._serve_sync):
            threading.Thread(target=target, daemon=True).start()

    def sensor(self, host_ns: int) -> int:
        return round((host_ns - self.host0) * (1 + self.drift)) + self.sensor0

    def host(self, sensor_ns: int) -> int:
        return round((sensor_ns - self.sensor0) / (1 + self.drift)) + self.host0

    def config(self, **fields) -> CameraConfig:
        return CameraConfig(
            role="body_2", source=STREAM, width=1920, height=1080, fps=30, notes="fake",
            stream_host="127.0.0.1", video_port=self._tcp.getsockname()[1],
            sync_port=self._udp.getsockname()[1], control_port=1, stats_port=2, **fields,
        )

    def _serve_video(self):
        while not self._done.is_set():
            try:
                conn, _ = self._tcp.accept()
            except OSError:
                return
            data, close = self.sessions[min(self.connections, len(self.sessions) - 1)]
            self.connections += 1
            conn.recv(1024)
            conn.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: video/h264\r\n\r\n" + data)
            if close:
                conn.close()
            else:
                self._open.append(conn)

    def _serve_sync(self):
        while True:
            try:
                data, addr = self._udp.recvfrom(64)
            except OSError:
                return
            token = int.from_bytes(data[:8], "big")
            s = self.sensor(time.time_ns())
            self._udp.sendto(stream_v1.sync_reply(token, s, s), addr)

    def close(self):
        self._done.set()
        for s in (self._tcp, self._udp, *self._open):
            s.close()


@pytest.fixture
def cameras():
    made = []
    yield lambda *a, **kw: made.append(FakeCamera(*a, **kw)) or made[-1]
    for cam in made:
        cam.close()


class BytesMuxer:
    def __init__(self, out: Path, fps: float):
        self.out = out
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data += data

    def close(self) -> None:
        self.out.write_bytes(self.data)


def source(cam: FakeCamera, **kw) -> StreamSource:
    kw.setdefault("muxer", BytesMuxer)
    return StreamSource(cam.config(), sync_probes=5, sync_interval_s=0.001, timeout_s=2, **kw)


def run_take(src: StreamSource, take_dir: Path, seconds: float = 0.2) -> list[Path]:
    src.prepare()
    src.start(take_dir)
    time.sleep(seconds)
    src.stop()
    return src.collect(take_dir)


def read_rows(path: Path) -> list[tuple[int, int]]:
    with open(path) as f:
        reader = csv.reader(f)
        assert tuple(next(reader)) == layout.TIMESTAMPS_COLUMNS
        return [(int(a), int(b)) for a, b in reader]


def past_sensor0(data: bytes) -> int:
    """A camera clock that puts these frames 10 s in the past."""
    first = next(f.timestamp.sensor_ns for f in stream_v1.frames(data) if f.timestamp)
    return first + 10_000_000_000


# ---------------------------------------------------------------- parsing

@pytest.mark.parametrize("name", ["decodable.h264", "tablet-excerpt.h264", "garbled.h264"])
def test_splitter_and_tracker_match_the_reference_reader(name):
    data = fixture(name) + AUD
    reference = stream_v1.frames(data)
    rng = random.Random(name)
    splitter, tracker, out = NalSplitter(), FrameTracker(), b""
    i = 0
    while i < len(data):
        n = rng.randint(1, 40)
        done, nals = splitter.feed(data[i:i + n])
        out += done
        for nal_type, nal in nals:
            tracker.add(nal_type, nal, 0)
        i += n
    assert out == data[: len(data) - len(AUD)]  # bytes unchanged; the AUD is held back
    assert [f.timestamp for f in tracker.frames] == [f.timestamp for f in reference]
    assert len(tracker.problems) == sum(1 for f in reference if f.problems)


def test_timestamp_without_its_slice_is_not_a_frame():
    tracker = FrameTracker()
    sei = stream_v1.build_timestamp_sei(1, 100, 100)[4:]
    tracker.add(stream_v1.NAL_SEI, sei, 0)
    tracker.drop_pending()  # connection lost before the slice
    tracker.add(stream_v1.NAL_SLICE, SLICE[4:], 0)
    assert [f.timestamp for f in tracker.frames] == [None]
    assert tracker.problems == ["frame 0: untimed (slice without a v1 timestamp SEI)"]


# ---------------------------------------------------------------- timing

def test_host_timestamps_remove_offset_and_drift():
    host0, sensor0, drift = 1_791_000_000_000_000_000, 35_000_000_000_000, -20e-6

    def sensor(h):
        return round((h - host0) * (1 + drift)) + sensor0

    def point(h):
        return SyncPoint(h, sensor(h), h - sensor(h))

    before, after = point(host0), point(host0 + 600_000_000_000)  # a 10-minute take
    truth = [host0 + 1_000_000_000 + k * 33_333_333 for k in range(0, 17_000, 997)]
    frames = [
        ReceivedFrame(i, stream_v1.Timestamp(i + 1, sensor(h), 0), 0) for i, h in enumerate(truth)
    ]
    got = host_timestamps(frames, before, after)
    assert [i for i, _ in got] == list(range(len(truth)))
    assert max(abs(ts - h) for (_, ts), h in zip(got, truth)) <= 2
    # without the drift correction, the end of the take would be ~12 ms off
    assert abs(host_timestamps(frames[-1:], before, before)[0][1] - truth[-1]) > 10_000_000


def test_sync_clock_finds_the_offset(cameras):
    cam = cameras([(b"", False)], sensor0=35_000_000_000_000)
    point = sync_clock("127.0.0.1", cam.config().sync_port, probes=20, interval_s=0.001)
    assert abs(point.offset_ns - (cam.host0 - cam.sensor0)) < 2_000_000
    assert abs(point.sensor_ns - cam.sensor(point.host_ns)) < 2_000_000


def test_sync_clock_without_answers_fails():
    silent = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    silent.bind(("127.0.0.1", 0))
    with silent, pytest.raises(StreamSourceError, match="at least 3 answered probes"):
        sync_clock("127.0.0.1", silent.getsockname()[1], probes=3, interval_s=0, timeout_s=0.01)


# ---------------------------------------------------------------- the source

def test_registered_and_satisfies_the_protocol(cameras):
    cam = cameras([(b"", False)])
    src = create_source(cam.config())
    assert type(src) is StreamSource
    assert isinstance(src, CameraSource)


@pytest.mark.parametrize("name", ["decodable", "tablet-excerpt"])
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_fixture_gives_the_right_frame_count(cameras, tmp_path, name):
    data = fixture(f"{name}.h264")
    cam = cameras([(data + AUD, False)], sensor0=past_sensor0(data))
    from mocap_capture.stream import FfmpegMuxer

    src = source(cam, muxer=FfmpegMuxer)
    video, timestamps = run_take(src, tmp_path)
    expected = fixture_rows(f"{name}.timestamps.csv")
    rows = read_rows(timestamps)
    assert [i for i, _ in rows] == [int(r["frame"]) for r in expected]
    packets = subprocess.run(
        ["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert int(packets) == len(expected)
    seqs = [int(r["seq"]) for r in expected]
    gaps = [f"gap: seq {a} → {b}" for a, b in zip(seqs, seqs[1:]) if b != a + 1]
    assert [p for p in src.problems if p.startswith("gap")] == [
        g + f", {int(g.split()[-1]) - int(g.split()[-3]) - 1} frame(s) missing" for g in gaps
    ]


def test_synthetic_offset_and_drift(cameras, tmp_path):
    t0 = time.time_ns() - 5_000_000_000
    cam = cameras([], sensor0=42_000_000_000_000, drift=2e-4)
    truth = {seq: t0 + seq * 33_333_333 for seq in range(1, 31)}
    data = synthetic(truth, lambda seq: cam.sensor(truth[seq])) + AUD
    cam.sessions = [(data, False)]
    src = source(cam)
    video, timestamps = run_take(src, tmp_path)
    rows = read_rows(timestamps)
    assert len(rows) == 30
    assert max(abs(ts - truth[i + 1]) for i, ts in rows) < 2_000_000
    assert video.read_bytes() == data[: len(data) - len(AUD)]
    assert src.problems == []


def test_dropped_connection_is_a_gap_never_papered_over(cameras, tmp_path):
    t0 = time.time_ns() - 5_000_000_000
    cam = cameras([], sensor0=42_000_000_000_000)
    sensor = lambda seq: cam.sensor(t0 + seq * 33_333_333)  # noqa: E731
    first = synthetic(range(1, 5), sensor)  # frame 4's slice is cut off by the drop
    second = synthetic(range(10, 16), sensor) + AUD
    cam.sessions = [(second, False), (first, True), (second, False)]  # prepare, take, reconnect
    src = source(cam, reconnect_delay_s=0.01)
    _, timestamps = run_take(src, tmp_path, seconds=0.5)
    rows = read_rows(timestamps)
    assert [i for i, _ in rows] == list(range(9))
    host = [ts for _, ts in rows]
    assert host == sorted(host)
    assert host[3] - host[2] > 6 * 33_333_333  # the gap is in the times too
    assert "connection lost after seq 3" in src.problems
    assert "reconnected after 3 frame(s)" in src.problems
    assert "gap: seq 3 → 10, 6 frame(s) missing" in src.problems


def test_untimed_frames_get_no_row(cameras, tmp_path):
    data = fixture("garbled.h264")
    cam = cameras([], sensor0=past_sensor0(data))
    cam.sessions = [(data + AUD, False)]
    src = source(cam)
    _, timestamps = run_take(src, tmp_path)
    assert [i for i, _ in read_rows(timestamps)] == [1]
    untimed = [p for p in src.problems if "untimed" in p]
    assert [p.split(":")[0] for p in untimed] == ["frame 0", "frame 2"]


def test_camera_without_v1_timestamps_fails_prepare(cameras):
    cam = cameras([(SPS + PPS + IDR + SLICE + AUD, False)])
    with pytest.raises(StreamSourceError, match="no frame with a v1 timestamp SEI"):
        source(cam).prepare()


def test_camera_that_refuses_fails_prepare(cameras):
    cam = cameras([(b"", False)])
    config = cam.config()
    cam.close()
    src = StreamSource(config, timeout_s=0.5)
    with pytest.raises(StreamSourceError, match="body_2"):
        src.prepare()


def test_start_before_prepare_fails(cameras, tmp_path):
    cam = cameras([(b"", False)])
    with pytest.raises(StreamSourceError, match="before prepare"):
        source(cam).start(tmp_path)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_ffmpeg_failure_keeps_only_the_tail_of_its_stderr(tmp_path):
    from mocap_capture.stream import ERROR_LINES, FfmpegMuxer

    muxer = FfmpegMuxer(tmp_path / "out.mkv", 30)
    muxer.write((SPS + PPS + IDR + SLICE) * 50)  # not decodable: FFmpeg can't write a header
    with pytest.raises(StreamSourceError) as e:
        muxer.close()
    message = str(e.value)
    assert "exited" in message
    assert len(message.splitlines()) <= ERROR_LINES + 1
