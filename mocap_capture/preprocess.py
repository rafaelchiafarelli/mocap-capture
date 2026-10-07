"""Preprocessing on the recorder, after the take, one role at a time.

    PreprocessSpec  crop (optional) then scale to the output size, encoded
                    FFV1 (lossless), CPU only
    none            the stream copied, never re-encoded

Either way every input frame becomes exactly one output frame with the same
timestamp (`-fps_mode passthrough`), so `raw/<role>.timestamps.csv` stays
valid for `prep/<role>.mkv`. The packet counts are compared afterwards and a
mismatch is an error, not a warning.

The spec comes from `take.json` (what the take was recorded with), and the
role's `applied_preprocess` is written back into it. Roles can run in
parallel: `take.json` is updated under a file lock.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from mocap_contracts import ContractError, PreprocessSpec, Take, from_json, layout, to_json

ERROR_LINES = 5  # of FFmpeg's stderr kept in an error, its last ones


class PreprocessError(RuntimeError):
    """A role that couldn't be preprocessed exactly."""


def preprocess_role(take_dir: Path, role: str) -> Path:
    """Write `prep/<role>.mkv` from `raw/<role>.mkv` and record what was applied."""
    camera = _camera(_read_take(take_dir), role)
    spec = camera.config.preprocess if camera.config.HasField("preprocess") else None
    raw = layout.raw_video(take_dir, role)
    if not raw.exists():
        raise PreprocessError(f"{role}: {raw} is missing")
    out = layout.prep_dir(take_dir) / f"{layout.check_id('role', role)}.mkv"
    out.parent.mkdir(exist_ok=True)
    tmp = out.with_suffix(".tmp.mkv")
    _ffmpeg(ffmpeg_cmd(raw, tmp, spec), role)
    raw_packets, prep_packets = packet_count(raw), packet_count(tmp)
    if raw_packets != prep_packets:
        tmp.unlink()
        raise PreprocessError(f"{role}: {raw_packets} frames in, {prep_packets} out")
    os.replace(tmp, out)
    if spec is not None:
        with take_lock(take_dir):
            take = _read_take(take_dir)
            _camera(take, role).applied_preprocess.CopyFrom(spec)
            _write_take(take_dir, take)
    return out


def ffmpeg_cmd(raw: Path, out: Path, spec: PreprocessSpec | None) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(raw),
           "-map", "0:v:0", "-an", "-fps_mode", "passthrough"]
    if spec is None:
        return cmd + ["-c", "copy", str(out)]
    filters = []
    if spec.HasField("crop"):
        c = spec.crop
        filters.append(f"crop={c.width}:{c.height}:{c.x}:{c.y}")
    filters.append(f"scale={spec.output_width}:{spec.output_height}")
    return cmd + ["-vf", ",".join(filters), "-c:v", "ffv1", "-level", "3", str(out)]


def packet_count(video: Path) -> int:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise PreprocessError(f"ffprobe {video}: {result.stderr.strip()}")
    return int(result.stdout.strip())


def _ffmpeg(cmd: list[str], role: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-ERROR_LINES:])
        raise PreprocessError(f"{role}: ffmpeg exited {result.returncode}:\n{tail}")


def _read_take(take_dir: Path) -> Take:
    path = layout.take_json(take_dir)
    try:
        return from_json(Take, path.read_text())
    except OSError as e:
        raise PreprocessError(f"{path}: {e.strerror}") from None
    except ContractError as e:
        raise PreprocessError(f"{path}: {e}") from None


def _write_take(take_dir: Path, take: Take) -> None:
    path = layout.take_json(take_dir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(to_json(take))
    os.replace(tmp, path)


def _camera(take: Take, role: str):
    for camera in take.cameras:
        if camera.config.role == role:
            return camera
    raise PreprocessError(f"take {take.id} has no camera {role!r}")


@contextmanager
def take_lock(take_dir: Path) -> Iterator[None]:
    """Held while take.json is rewritten (here) or copied (the hand-off)."""
    with open(take_dir / ".take.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
