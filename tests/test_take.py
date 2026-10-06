import itertools
from pathlib import Path

import pytest
import yaml
from mocap_contracts import Flag, Take, TakeReport, TakeType, from_json, layout

from mocap_capture import cli
from mocap_capture.config import load_config
from mocap_capture.sync import END, START, ManualTrigger
from mocap_capture.take import TakeError, run_take

PERFORMANCE = TakeType.Value("TAKE_TYPE_PERFORMANCE")
CALIBRATION = TakeType.Value("TAKE_TYPE_CALIBRATION")


def stream_camera(role: str, last_octet: int) -> dict:
    return {
        "role": role, "source": "CAMERA_SOURCE_STREAM", "width": 1920, "height": 1080,
        "fps": 30, "notes": "tablet", "stream_host": f"192.168.1.{last_octet}",
        "video_port": 8080, "sync_port": 8081, "control_port": 8082, "stats_port": 8083,
    }


class Clock:
    def __init__(self):
        self._ticks = itertools.count(1_000)

    def __call__(self) -> int:
        return next(self._ticks)


class FakeSource:
    """Records what the take did to it, on the shared clock."""

    def __init__(self, config, log, clock, fail=None):
        self.config, self.log, self.clock, self.fail = config, log, clock, fail or set()
        self.problems = []

    def _call(self, what):
        self.log.append((what, self.config.role, self.clock()))
        if what in self.fail:
            raise RuntimeError(f"{what} broke")

    def prepare(self):
        self._call("prepare")

    def start(self, take_dir):
        self._call("start")
        layout.raw_dir(take_dir).mkdir(exist_ok=True)
        layout.raw_video(take_dir, self.config.role).write_bytes(b"video")

    def stop(self):
        self._call("stop")

    def collect(self, take_dir):
        self._call("collect")
        ts = layout.raw_timestamps(take_dir, self.config.role)
        ts.write_text("frame,host_ts_ns\n")
        return [layout.raw_video(take_dir, self.config.role), ts]


@pytest.fixture
def setup(tmp_path):
    data = {"storage": {"root": str(tmp_path / "data")}, "report": {"max_gap_ms": 100},
            "cameras": [stream_camera("body_1", 21), stream_camera("body_2", 22)]}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data))
    clock, log, fail = Clock(), [], {}

    def make_source(config):
        return FakeSource(config, log, clock, fail.get(config.role))

    class Setup:
        pass

    s = Setup()
    s.config_path, s.config, s.clock, s.log, s.fail = path, load_config(path), clock, log, fail
    s.make_source = make_source
    s.take_dir = tmp_path / "data" / "S1" / "takes" / "T1"
    s.reported = []

    def run(**kw):
        kw.setdefault("wait_for_end", lambda: s.log.append(("operator ends", None, clock())))
        return run_take(s.config, "S1", "T1", PERFORMANCE, trigger=ManualTrigger(clock),
                        make_source=make_source, report=s.reported.append, **kw)

    s.run = run
    return s


def read_take(take_dir: Path) -> Take:
    return from_json(Take, layout.take_json(take_dir).read_text())


def when(log, what, role=None):
    return next(t for w, r, t in log if w == what and (role is None or r == role))


def test_end_to_end_fake_take(setup):
    take_dir = setup.run()
    assert take_dir == setup.take_dir
    take = read_take(take_dir)
    assert (take.id, take.session_id, take.type) == ("T1", "S1", PERFORMANCE)
    assert [c.config.role for c in take.cameras] == ["body_1", "body_2"]
    assert take.cameras[1].config.stream_host == "192.168.1.22"
    assert (take.start.kind, take.end.kind) == (START, END)

    calls = [(w, r) for w, r, _ in setup.log]
    assert calls == [
        ("prepare", "body_1"), ("prepare", "body_2"),
        ("start", "body_1"), ("start", "body_2"),
        ("operator ends", None),
        ("stop", "body_1"), ("stop", "body_2"),
        ("collect", "body_1"), ("collect", "body_2"),
    ]
    # START after every source started, END before any stopped
    assert take.start.host_ts_ns > when(setup.log, "start", "body_2")
    assert when(setup.log, "operator ends") < take.end.host_ts_ns < when(setup.log, "stop", "body_1")
    for role in ("body_1", "body_2"):
        assert layout.raw_video(take_dir, role).exists()
        assert layout.raw_timestamps(take_dir, role).exists()
    assert "body_1: raw/body_1.mkv, raw/body_1.timestamps.csv" in setup.reported


def test_take_json_exists_while_recording(setup):
    seen = {}

    def peek():
        seen["take"] = read_take(setup.take_dir)

    setup.run(wait_for_end=peek)
    assert seen["take"].start.kind == START
    assert not seen["take"].HasField("end")


def test_ctrl_c_ends_the_take_cleanly(setup):
    def interrupt():
        raise KeyboardInterrupt

    setup.run(wait_for_end=interrupt)
    assert read_take(setup.take_dir).end.kind == END


def test_source_not_ready_stops_before_anything_is_created(setup):
    setup.fail["body_2"] = {"prepare"}
    with pytest.raises(TakeError, match="role body_2 not ready: prepare broke"):
        setup.run()
    assert not setup.take_dir.exists()
    assert [w for w, _, _ in setup.log] == ["prepare", "prepare"]


def test_start_failure_stops_the_started_sources(setup):
    setup.fail["body_2"] = {"start"}
    with pytest.raises(TakeError, match="role body_2 failed to start: start broke.*no take.json"):
        setup.run()
    assert ("stop", "body_1") in [(w, r) for w, r, _ in setup.log]
    assert not layout.take_json(setup.take_dir).exists()


def test_stop_failure_still_closes_the_take(setup):
    setup.fail["body_1"] = {"stop"}
    with pytest.raises(TakeError, match="take closed with failures: role body_1 failed to stop"):
        setup.run()
    calls = [(w, r) for w, r, _ in setup.log]
    assert ("stop", "body_2") in calls and ("collect", "body_1") in calls
    assert read_take(setup.take_dir).end.kind == END


def test_source_problems_are_reported(setup):
    def make_source(config):
        src = setup.make_source(config)
        src.problems = ["gap: seq 3 → 10, 6 frame(s) missing"]
        return src

    run_take(setup.config, "S1", "T1", PERFORMANCE, wait_for_end=lambda: None,
             make_source=make_source, report=setup.reported.append)
    assert "body_1: gap: seq 3 → 10, 6 frame(s) missing" in setup.reported


def test_existing_take_is_never_overwritten(setup):
    setup.take_dir.mkdir(parents=True)
    with pytest.raises(TakeError, match="already exists"):
        setup.run()
    assert setup.log == []


def test_unregistered_source_kind_is_an_error(tmp_path):
    data = yaml.safe_load((Path(__file__).parent / "fixtures" / "config.yaml").read_text())
    data["storage"]["root"] = str(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(TakeError, match="body_1: no source registered for CAMERA_SOURCE_UVC"):
        run_take(load_config(path), "S1", "T1", PERFORMANCE, wait_for_end=lambda: None)


def test_calibration_needs_the_board(setup):
    with pytest.raises(TakeError, match="CALIBRATION take needs the declared board"):
        run_take(setup.config, "S1", "T1", CALIBRATION, wait_for_end=lambda: None,
                 make_source=setup.make_source)
    assert setup.log == []


@pytest.mark.parametrize("session, name", [("bad/id", "T1"), ("S1", "../escape")])
def test_ids_must_be_folder_names(setup, session, name):
    with pytest.raises(TakeError, match="invalid"):
        run_take(setup.config, session, name, PERFORMANCE, wait_for_end=lambda: None,
                 make_source=setup.make_source)


def test_cli_take(setup, monkeypatch, capsys):
    import mocap_capture.take as take_module

    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    monkeypatch.setattr(take_module, "run_take", _with_default_source(take_module.run_take, setup))
    argv = ["take", "--config", str(setup.config_path), "--session", "S1", "--name", "T1",
            "--type", "PERFORMANCE"]
    assert cli.main(argv) == 0
    assert read_take(setup.take_dir).end.kind == END
    assert cli.main(argv) == 1
    assert "already exists" in capsys.readouterr().err


def _with_default_source(run, setup):
    def wrapped(*args, **kw):
        kw.setdefault("make_source", setup.make_source)
        return run(*args, **kw)
    return wrapped


def test_cli_bad_config(tmp_path, capsys):
    argv = ["take", "--config", str(tmp_path / "missing.yaml"), "--session", "S1",
            "--name", "T1", "--type", "PERFORMANCE"]
    assert cli.main(argv) == 1
    assert "No such file" in capsys.readouterr().err


# ---------------------------------------------------------------- sync integration (sync/2)

def test_sync_events_on_the_real_clock_bracket_the_recording(setup):
    import time

    real_log = []

    def make_source(config):
        return FakeSource(config, real_log, time.time_ns)

    take_dir = run_take(setup.config, "S1", "T1", PERFORMANCE, wait_for_end=lambda: None,
                        make_source=make_source, report=lambda _: None)
    take = read_take(take_dir)
    last_start = max(t for w, _, t in real_log if w == "start")
    first_stop = min(t for w, _, t in real_log if w == "stop")
    assert last_start <= take.start.host_ts_ns <= take.end.host_ts_ns <= first_stop


def test_no_start_marker_when_a_source_fails_to_start(setup):
    trigger = ManualTrigger(setup.clock)
    setup.fail["body_2"] = {"start"}
    with pytest.raises(TakeError):
        run_take(setup.config, "S1", "T1", PERFORMANCE, wait_for_end=lambda: None,
                 trigger=trigger, make_source=setup.make_source, report=lambda _: None)
    assert trigger.start is None and trigger.end is None


def test_end_marker_precedes_every_stop_even_when_one_fails(setup):
    setup.fail["body_1"] = {"stop"}
    with pytest.raises(TakeError):
        setup.run()
    take = read_take(setup.take_dir)
    stops = [t for w, _, t in setup.log if w == "stop"]
    assert len(stops) == 2 and take.end.host_ts_ns < min(stops)


def test_take_writes_its_report(setup):
    take_dir = setup.run()
    report = from_json(TakeReport, layout.report_json(take_dir).read_text())
    assert report.take_id == "T1"
    assert report.ok == Flag.Value("FLAG_OFF")  # the fake sources wrote no timestamps
    assert any(line.startswith("take T1: NOT OK") for line in setup.reported)
