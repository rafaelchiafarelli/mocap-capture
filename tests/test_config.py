from pathlib import Path

import pytest
import yaml
from mocap_contracts import CameraSource

from mocap_capture.config import ConfigError, load_config

FIXTURE = Path(__file__).parent / "fixtures" / "config.yaml"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text())


def _write(tmp_path: Path, data) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(data if isinstance(data, str) else yaml.safe_dump(data))
    return path


def test_valid_config():
    config = load_config(FIXTURE)
    assert config.storage_root == Path("/data/mocap")
    assert config.max_gap_ms == 100
    assert config.post_roll_ms == 500
    uvc, stream = config.cameras
    assert uvc.role == "body_1"
    assert uvc.source == CameraSource.Value("CAMERA_SOURCE_UVC")
    assert uvc.controls[0].key == "exposure_time_absolute"
    assert uvc.controls[0].value.int_value == 150
    assert stream.source == CameraSource.Value("CAMERA_SOURCE_STREAM")
    assert stream.stream_host == "192.168.1.21"
    assert stream.preprocess.output_width == 960
    assert config.preprocess("body_1") is None
    assert config.preprocess("body_2").crop.width == 1440
    with pytest.raises(KeyError):
        config.preprocess("body_9")


def _drop(field):
    def edit(data):
        del data["cameras"][0][field]
    return edit


def _set(i, field, value):
    def edit(data):
        data["cameras"][i][field] = value
    return edit


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda d: d.update(handoff={}), "unknown section(s) ['handoff']"),
        (lambda d: d.pop("storage"), "storage must be a mapping with root"),
        (lambda d: d.update(storage={"root": "data"}), "storage.root must be an absolute path"),
        (lambda d: d.update(storage={}), "storage.root must be an absolute path"),
        (lambda d: d["storage"].update(free_gb=50), "storage: unknown key(s) ['free_gb']"),
        (lambda d: d.pop("report"), "report must be a mapping with max_gap_ms"),
        (lambda d: d.update(report={"max_gap_ms": 0}), "report.max_gap_ms must be a positive number"),
        (lambda d: d.update(report={"max_gap_ms": "100"}), "report.max_gap_ms must be a positive number"),
        (lambda d: d["report"].update(min_fps=25), "report: unknown key(s) ['min_fps']"),
        (lambda d: d.pop("take"), "take must be a mapping with post_roll_ms"),
        (lambda d: d.update(take={"post_roll_ms": -1}), "take.post_roll_ms must be a non-negative number"),
        (lambda d: d.pop("cameras"), "cameras must be a non-empty list"),
        (lambda d: d.update(cameras=[]), "cameras must be a non-empty list"),
        (_drop("notes"), "missing required field(s) ['notes']"),
        (_set(0, "lens", "wide"), "unknown field(s) ['lens']"),
        (_set(0, "source", "CAMERA_SOURCE_UNSET"), "hold their UNSET value"),
        (_set(0, "fps", 0), "fps must be positive"),
        (_drop("device_hint"), "a UVC camera needs device_hint"),
        (_set(1, "video_port", 70000), "ports must be 1..65535"),
        (_set(1, "role", "body_1"), "duplicate role(s) ['body_1']"),
        (_drop("preprocess"), "cameras[0]: preprocess must be declared (a spec, or none)"),
        (_set(0, "preprocess", None), "preprocess must be a spec or none, got None"),
        (_set(0, "preprocess", "None"), "preprocess must be a spec or none, got 'None'"),
        (_set(1, "preprocess", {"output_width": 960}), "missing required field(s) ['output_height']"),
        (_set(1, "preprocess", {"crop": {"x": 1000, "y": 0, "width": 1440, "height": 1080},
                                "output_width": 960, "output_height": 720}),
         "crop 1000,0 1440x1080 is outside the 1920x1080 source frame"),
        (_set(1, "preprocess", {"crop": {"x": -1, "y": 0, "width": 10, "height": 10},
                                "output_width": 960, "output_height": 720}),
         "crop needs x, y >= 0"),
    ],
)
def test_invalid_config(tmp_path, edit, message):
    data = _fixture()
    edit(data)
    with pytest.raises(ConfigError) as e:
        load_config(_write(tmp_path, data))
    assert message in str(e.value)


@pytest.mark.parametrize(
    "text, message",
    [
        ("cameras: [", "invalid YAML"),
        ("- just a list", "expected a mapping at the top level"),
        ("", "expected a mapping at the top level"),
    ],
)
def test_invalid_yaml(tmp_path, text, message):
    with pytest.raises(ConfigError) as e:
        load_config(_write(tmp_path, text))
    assert message in str(e.value)


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="No such file"):
        load_config(tmp_path / "nope.yaml")


def test_errors_name_the_camera(tmp_path):
    data = _fixture()
    data["cameras"][1]["fps"] = -1
    with pytest.raises(ConfigError, match=r"cameras\[1\]"):
        load_config(_write(tmp_path, data))
