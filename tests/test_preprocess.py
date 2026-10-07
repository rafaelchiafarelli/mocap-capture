import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from mocap_contracts import (
    CameraConfig,
    CameraSource,
    Crop,
    PreprocessSpec,
    SyncEvent,
    SyncKind,
    SyncSource,
    Take,
    TakeCamera,
    TakeType,
    from_json,
    layout,
    to_json,
)

from mocap_capture import preprocess
from mocap_capture.preprocess import PreprocessError, ffmpeg_cmd, preprocess_role

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg"
)

SPEC = PreprocessSpec(crop=Crop(x=40, y=20, width=240, height=200), output_width=120, output_height=100)


def make_raw(path: Path) -> None:
    """30 H.264 frames at 30 fps, 320x240, with frame 10 missing (a gap in the timestamps)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "testsrc=size=320x240:rate=30", "-frames:v", "30",
         "-vf", "select='not(eq(n\\,10))'", "-fps_mode", "passthrough",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


def camera(role: str, spec: PreprocessSpec | None) -> TakeCamera:
    config = CameraConfig(
        role=role, source=CameraSource.Value("CAMERA_SOURCE_STREAM"), width=320, height=240,
        fps=30, notes="", stream_host="10.0.0.1", video_port=1, sync_port=2, control_port=3,
        stats_port=4,
    )
    if spec is not None:
        config.preprocess.CopyFrom(spec)
    return TakeCamera(config=config)


@pytest.fixture(scope="module")
def raw_video(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("raw") / "source.mkv"
    make_raw(path)
    return path


@pytest.fixture
def take_dir(tmp_path, raw_video) -> Path:
    take_dir = tmp_path / "S1" / "takes" / "T1"
    take = Take(id="T1", session_id="S1", type=TakeType.Value("TAKE_TYPE_PERFORMANCE"),
                start=SyncEvent(kind=SyncKind.Value("SYNC_KIND_START"), host_ts_ns=1,
                                source=SyncSource.Value("SYNC_SOURCE_MANUAL")))
    take.end.CopyFrom(SyncEvent(kind=SyncKind.Value("SYNC_KIND_END"), host_ts_ns=2,
                                source=SyncSource.Value("SYNC_SOURCE_MANUAL")))
    take.cameras.extend([camera("body_1", SPEC), camera("body_2", None)])
    for role in ("body_1", "body_2"):
        layout.raw_dir(take_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(raw_video, layout.raw_video(take_dir, role))
    layout.take_json(take_dir).write_text(to_json(take))
    return take_dir


def probe(video: Path, entries: str) -> list[str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def frame_md5s(video: Path) -> list[str]:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0:v",
         "-c", "copy", "-f", "framemd5", "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line.split(",")[-1].strip() for line in out.splitlines() if not line.startswith("#")]


def times(video: Path) -> list[float]:
    """Presentation times in order (packets come in decode order)."""
    return sorted(float(t) for t in probe(video, "packet=pts_time"))


def read_take(take_dir: Path) -> Take:
    return from_json(Take, layout.take_json(take_dir).read_text())


def test_spec_crops_scales_and_keeps_every_frame_and_its_time(take_dir):
    raw = layout.raw_video(take_dir, "body_1")
    out = preprocess_role(take_dir, "body_1")
    assert out == take_dir / "prep" / "body_1.mkv"
    assert probe(out, "stream=codec_name,width,height") == ["ffv1,120,100"]
    assert len(probe(out, "packet=pts")) == len(probe(raw, "packet=pts")) == 30
    assert times(out) == times(raw)
    assert times(out)[10] - times(out)[9] == pytest.approx(2 / 30, abs=1e-3)  # the gap stays a gap
    take = read_take(take_dir)
    assert take.cameras[0].applied_preprocess == SPEC
    assert not take.cameras[1].HasField("applied_preprocess")


def test_none_is_a_byte_copy_of_the_stream(take_dir):
    raw = layout.raw_video(take_dir, "body_2")
    out = preprocess_role(take_dir, "body_2")
    assert probe(out, "stream=codec_name") == ["h264"]
    assert frame_md5s(out) == frame_md5s(raw)
    assert times(out) == times(raw)
    assert not read_take(take_dir).cameras[1].HasField("applied_preprocess")


def test_roles_in_parallel_both_recorded(take_dir):
    take = read_take(take_dir)
    take.cameras.append(camera("body_3", SPEC))
    layout.take_json(take_dir).write_text(to_json(take))
    shutil.copy(layout.raw_video(take_dir, "body_1"), layout.raw_video(take_dir, "body_3"))
    threads = [threading.Thread(target=preprocess_role, args=(take_dir, r)) for r in ("body_1", "body_3")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    applied = {c.config.role: c.HasField("applied_preprocess") for c in read_take(take_dir).cameras}
    assert applied == {"body_1": True, "body_2": False, "body_3": True}


def test_frame_count_mismatch_is_an_error(take_dir, monkeypatch):
    counts = iter([30, 29])
    monkeypatch.setattr(preprocess, "packet_count", lambda _: next(counts))
    with pytest.raises(PreprocessError, match="body_1: 30 frames in, 29 out"):
        preprocess_role(take_dir, "body_1")
    assert list((take_dir / "prep").iterdir()) == []
    assert not read_take(take_dir).cameras[0].HasField("applied_preprocess")


def test_broken_raw_fails_with_a_short_error(take_dir):
    layout.raw_video(take_dir, "body_1").write_bytes(b"not a video" * 100)
    with pytest.raises(PreprocessError) as e:
        preprocess_role(take_dir, "body_1")
    assert "ffmpeg exited" in str(e.value)
    assert len(str(e.value).splitlines()) <= preprocess.ERROR_LINES + 1


def test_missing_raw_and_unknown_role(take_dir):
    layout.raw_video(take_dir, "body_2").unlink()
    with pytest.raises(PreprocessError, match="body_2.mkv is missing"):
        preprocess_role(take_dir, "body_2")
    with pytest.raises(PreprocessError, match="no camera 'body_9'"):
        preprocess_role(take_dir, "body_9")


def test_command_is_cpu_only_and_passthrough():
    cmd = ffmpeg_cmd(Path("raw.mkv"), Path("out.mkv"), SPEC)
    assert cmd[cmd.index("-vf") + 1] == "crop=240:200:40:20,scale=120:100"
    assert cmd[cmd.index("-c:v") + 1] == "ffv1"
    assert cmd[cmd.index("-fps_mode") + 1] == "passthrough"
    assert not any("cuda" in a or "nvenc" in a or "hwaccel" in a for a in cmd)
    no_crop = PreprocessSpec(output_width=160, output_height=120)
    cmd = ffmpeg_cmd(Path("raw.mkv"), Path("out.mkv"), no_crop)
    assert cmd[cmd.index("-vf") + 1] == "scale=160:120"
    assert ffmpeg_cmd(Path("raw.mkv"), Path("out.mkv"), None)[-3:] == ["-c", "copy", "out.mkv"]
