import shutil
import threading
from pathlib import Path

import pytest
from mocap_contracts import (
    CameraConfig,
    CameraFileReady,
    CameraSource,
    FileKind,
    Session,
    SyncEvent,
    SyncKind,
    SyncSource,
    PreprocessSpec,
    Take,
    TakeCamera,
    TakeClosed,
    TakeType,
    from_json,
    layout,
    to_json,
)

from mocap_capture import send as send_module
from mocap_capture import transfer
from mocap_capture.handoff import HandoffError
from mocap_capture.preprocess import take_lock
from mocap_capture.send import handoff_take
from mocap_capture.transfer import LocalTarget

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="needs rsync")
ROLES = ("body_1", "body_2")


def sync(kind: str, ts: int) -> SyncEvent:
    return SyncEvent(kind=SyncKind.Value(f"SYNC_KIND_{kind}"), host_ts_ns=ts,
                     source=SyncSource.Value("SYNC_SOURCE_MANUAL"))


class Journal:
    """Every file copied and every event sent, in order."""

    def __init__(self):
        self.entries: list[str] = []
        self.lock = threading.Lock()

    def add(self, entry: str):
        with self.lock:
            self.entries.append(entry)


class FakePublisher:
    def __init__(self, journal):
        self.journal = journal
        self.events = []

    def send(self, event):
        self.events.append(event)
        if isinstance(event, TakeClosed):
            self.journal.add("event TakeClosed")
        else:
            kind = FileKind.Name(event.kind).removeprefix("FILE_KIND_")
            self.journal.add(f"event {kind} {event.role}")


class Setup:
    def __init__(self, tmp_path, monkeypatch):
        self.root = tmp_path / "recorder"
        self.target = LocalTarget(tmp_path / "processing")
        self.target.root.mkdir()
        self.take_dir = self.root / "S1" / "takes" / "T1"
        self.journal = Journal()
        self.publisher = FakePublisher(self.journal)
        self.preprocessed = []
        self.preprocess_hook = {}
        layout.raw_dir(self.take_dir).mkdir(parents=True)
        self.write_session()
        take = Take(id="T1", session_id="S1", type=TakeType.Value("TAKE_TYPE_PERFORMANCE"),
                    start=sync("START", 1_000), end=sync("END", 9_000))
        for i, role in enumerate(ROLES):
            take.cameras.append(TakeCamera(config=CameraConfig(
                role=role, source=CameraSource.Value("CAMERA_SOURCE_STREAM"), width=64, height=64,
                fps=30, notes="", stream_host=f"10.0.0.{i}", video_port=1, sync_port=2,
                control_port=3, stats_port=4,
            )))
            layout.raw_timestamps(self.take_dir, role).write_text(
                "frame,host_ts_ns\n0,500\n1,4000\n2,9500\n")
            layout.raw_video(self.take_dir, role).write_bytes(f"raw {role}".encode())
        layout.take_json(self.take_dir).write_text(to_json(take))
        layout.report_json(self.take_dir).write_text("{}\n")

        real_rsync = transfer._rsync
        monkeypatch.setattr(transfer, "_rsync", self._logged(real_rsync))
        monkeypatch.setattr(send_module, "packet_count", lambda path: 3)

    def write_session(self):
        path = layout.session_json(self.root, "S1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(to_json(Session(id="S1", date="2026-10-06")))

    def _logged(self, real):
        def rsync(source, rel, target):
            self.journal.add(f"file {Path(*rel.parts[3:]) if len(rel.parts) > 3 else rel.parts[-1]}")
            return real(source, rel, target)
        return rsync

    def preprocess(self, take_dir, role):
        """Like the real one: writes prep/ and records applied_preprocess in take.json."""
        self.preprocess_hook.get(role, lambda: None)()
        self.preprocessed.append(role)
        with take_lock(take_dir):
            take = from_json(Take, layout.take_json(take_dir).read_text())
            cam = next(c for c in take.cameras if c.config.role == role)
            cam.applied_preprocess.CopyFrom(PreprocessSpec(output_width=32, output_height=32))
            layout.take_json(take_dir).write_text(to_json(take))
        out = take_dir / "prep" / f"{role}.mkv"
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(f"prep {role}".encode())
        return out

    def run(self):
        handoff_take(self.take_dir, self.root, self.target, self.publisher,
                     report=lambda _: None, preprocess=self.preprocess)

    def remote(self, rel: str) -> Path:
        return self.target.root / "S1" / "takes" / "T1" / rel


@pytest.fixture
def setup(tmp_path, monkeypatch):
    return Setup(tmp_path, monkeypatch)


def test_order_session_take_timestamps_closed_then_videos(setup):
    setup.run()
    e = setup.journal.entries
    closing = [
        "file session.json", "file take.json",
        "file raw/body_1.timestamps.csv", "file raw/body_1.timestamps.csv.ready.json",
        "event TIMESTAMPS body_1",
        "file raw/body_2.timestamps.csv", "file raw/body_2.timestamps.csv.ready.json",
        "event TIMESTAMPS body_2",
        "file closed.json", "event TakeClosed",
    ]
    assert e[:len(closing)] == closing
    for role in ROLES:
        video = [f"file prep/{role}.mkv", f"file prep/{role}.mkv.ready.json", f"event VIDEO {role}"]
        positions = [e.index(x) for x in video]
        assert positions == sorted(positions) and positions[0] > e.index("event TakeClosed")
        # take.json went again after TakeClosed, before this role's video
        resent = [i for i, x in enumerate(e) if x == "file take.json" and i > e.index("event TakeClosed")]
        assert resent and min(resent) < positions[0]
    assert e[-1] == "file report.json"
    assert not any("raw/" in x and x.endswith(".mkv") for x in e)  # raw videos stay on the recorder


def test_what_arrived_matches_its_sidecars(setup):
    setup.run()
    assert (setup.target.root / "S1" / "session.json").exists()
    for role in ROLES:
        for rel, kind in ((f"raw/{role}.timestamps.csv", "FILE_KIND_TIMESTAMPS"),
                          (f"prep/{role}.mkv", "FILE_KIND_VIDEO")):
            ready = from_json(CameraFileReady, setup.remote(rel + ".ready.json").read_text())
            assert ready.kind == FileKind.Value(kind) and ready.path == rel
            assert ready.size_bytes == setup.remote(rel).stat().st_size
            assert ready.sha256 == transfer._sha256(setup.remote(rel))
            assert (ready.frames, ready.first_ts_ns, ready.last_ts_ns) == (3, 500, 9500)
    take = from_json(Take, setup.remote("take.json").read_text())
    assert all(c.HasField("applied_preprocess") for c in take.cameras)
    closed = from_json(TakeClosed, setup.remote("closed.json").read_text())
    assert list(closed.roles) == list(ROLES) and closed.end.host_ts_ns == 9_000


def test_a_slow_role_does_not_delay_the_others(setup):
    body_2_done = threading.Event()
    original_send = setup.publisher.send

    def send(event):
        original_send(event)
        if getattr(event, "role", None) == "body_2" and event.kind == FileKind.Value("FILE_KIND_VIDEO"):
            body_2_done.set()

    setup.publisher.send = send
    setup.preprocess_hook["body_1"] = lambda: body_2_done.wait(5)  # body_1 finishes only after body_2
    setup.run()
    e = setup.journal.entries
    assert body_2_done.is_set()
    assert e.index("event VIDEO body_2") < e.index("event VIDEO body_1")


def test_resend_sends_only_what_is_missing(setup):
    setup.run()
    inodes = {p: p.stat().st_ino for p in setup.target.root.rglob("*") if p.is_file()}
    setup.remote("prep/body_2.mkv").unlink()
    setup.preprocessed.clear()
    setup.run()
    assert setup.preprocessed == []  # prep/ already there
    for path, ino in inodes.items():
        if path != setup.remote("prep/body_2.mkv"):
            assert path.stat().st_ino == ino, f"{path} was copied again"
    assert setup.remote("prep/body_2.mkv").read_bytes() == b"prep body_2"


def test_missing_session_json_stops_before_anything_is_sent(setup):
    layout.session_json(setup.root, "S1").unlink()
    with pytest.raises(HandoffError, match="session.json is missing; write it, then run mocap-capture send"):
        setup.run()
    assert list(setup.target.root.rglob("*")) == []
    assert setup.publisher.events == []
    assert sorted(setup.preprocessed) == list(ROLES)  # done meanwhile, ready for the resend

    setup.write_session()
    setup.run()
    assert setup.remote("prep/body_1.mkv").exists() and setup.remote("closed.json").exists()


def test_session_json_for_another_session_is_refused(setup):
    layout.session_json(setup.root, "S1").write_text(to_json(Session(id="S2", date="2026-10-06")))
    with pytest.raises(HandoffError, match="is for session 'S2'"):
        setup.run()


def test_take_without_end_sends_nothing(setup):
    take = from_json(Take, layout.take_json(setup.take_dir).read_text())
    take.ClearField("end")
    layout.take_json(setup.take_dir).write_text(to_json(take))
    with pytest.raises(HandoffError, match="never closed"):
        setup.run()
    assert setup.journal.entries == []


def test_a_failing_role_is_reported_after_the_others_finish(setup):
    def broken():
        raise RuntimeError("ffmpeg broke")

    setup.preprocess_hook["body_1"] = broken
    with pytest.raises(HandoffError, match="body_1: ffmpeg broke"):
        setup.run()
    assert "event VIDEO body_2" in setup.journal.entries


def test_cli_send(setup, tmp_path, monkeypatch, capsys):
    import yaml

    from mocap_capture import cli, handoff

    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({
        "storage": {"root": str(setup.root)}, "take": {"post_roll_ms": 0},
        "report": {"max_gap_ms": 100},
        "handoff": {"host": "127.0.0.1", "take_closed_port": 5600, "file_ready_port": 5601,
                    "ssh_user": "rafael", "data_root": "/data/mocap"},
        "cameras": [{"role": "body_1", "source": "CAMERA_SOURCE_STREAM", "width": 64, "height": 64,
                     "fps": 30, "notes": "", "stream_host": "10.0.0.1", "video_port": 1,
                     "sync_port": 2, "control_port": 3, "stats_port": 4, "preprocess": "none"}],
    }))
    monkeypatch.setattr(transfer.SshTarget, "from_config", classmethod(lambda cls, h: setup.target))
    monkeypatch.setattr(handoff.Publisher, "__init__", lambda self, h, ctx=None: None)
    monkeypatch.setattr(handoff.Publisher, "send", lambda self, e: setup.publisher.send(e))
    monkeypatch.setattr(handoff.Publisher, "close", lambda self, flush_ms=0: None)
    monkeypatch.setattr(send_module, "preprocess_role", setup.preprocess)
    argv = ["send", "--config", str(config), "--session", "S1", "--take", "T1"]
    assert cli.main(argv) == 0
    assert setup.remote("closed.json").exists()
    layout.session_json(setup.root, "S1").unlink()
    assert cli.main(argv) == 1
    assert "session.json is missing" in capsys.readouterr().err
