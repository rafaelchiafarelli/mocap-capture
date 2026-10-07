from pathlib import Path

import pytest
from mocap_contracts import CameraConfig, layout
from mocap_contracts import CameraSource as SourceKind

from mocap_capture import sources
from mocap_capture.config import load_config
from mocap_capture.sources import CameraSource, create_source, register

FIXTURE = Path(__file__).parent / "fixtures" / "config.yaml"
UVC = SourceKind.Value("CAMERA_SOURCE_UVC")
STREAM = SourceKind.Value("CAMERA_SOURCE_STREAM")


class FakeSource:
    def __init__(self, config: CameraConfig):
        self.config = config
        self.calls: list[str] = []

    def prepare(self) -> None:
        self.calls.append("prepare")

    def start(self, take_dir: Path) -> None:
        self.calls.append("start")
        layout.raw_dir(take_dir).mkdir(parents=True, exist_ok=True)
        layout.raw_video(take_dir, self.config.role).write_bytes(b"")

    def stop(self) -> None:
        self.calls.append("stop")

    def collect(self, take_dir: Path) -> list[Path]:
        self.calls.append("collect")
        timestamps = layout.raw_timestamps(take_dir, self.config.role)
        timestamps.write_text("frame,host_ts_ns\n")
        return [layout.raw_video(take_dir, self.config.role), timestamps]


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(sources, "_REGISTRY", {})


@pytest.fixture
def cameras():
    return {c.role: c for c in load_config(FIXTURE).cameras}


def test_fake_source_satisfies_the_protocol(cameras):
    assert isinstance(FakeSource(cameras["body_1"]), CameraSource)


def test_missing_method_does_not_satisfy_the_protocol(cameras):
    class NoCollect:
        config = cameras["body_1"]

        def prepare(self): ...
        def start(self, take_dir): ...
        def stop(self): ...

    assert not isinstance(NoCollect(), CameraSource)


def test_registry_picks_the_source_by_kind(cameras):
    class FakeStream(FakeSource):
        pass

    register(UVC)(FakeSource)
    register(STREAM)(FakeStream)
    assert type(create_source(cameras["body_1"])) is FakeSource
    assert type(create_source(cameras["body_2"])) is FakeStream
    assert create_source(cameras["body_2"]).config is cameras["body_2"]


def test_unregistered_kind_is_an_error(cameras):
    register(UVC)(FakeSource)
    with pytest.raises(LookupError, match="body_2: no source registered for CAMERA_SOURCE_STREAM"):
        create_source(cameras["body_2"])


def test_double_registration_is_an_error():
    register(UVC)(FakeSource)
    with pytest.raises(ValueError, match="already registered"):
        register(UVC)(FakeSource)


def test_unset_kind_cannot_be_registered():
    with pytest.raises(ValueError, match="CAMERA_SOURCE_UNSET"):
        register(0)


def test_lifecycle_writes_under_raw(cameras, tmp_path):
    register(UVC)(FakeSource)
    source = create_source(cameras["body_1"])
    source.prepare()
    source.start(tmp_path)
    source.stop()
    files = source.collect(tmp_path)
    assert source.calls == ["prepare", "start", "stop", "collect"]
    assert files == [tmp_path / "raw" / "body_1.mkv", tmp_path / "raw" / "body_1.timestamps.csv"]
    assert all(f.exists() for f in files)
