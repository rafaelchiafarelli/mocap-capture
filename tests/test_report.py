import random
from pathlib import Path

import pytest
import yaml
from mocap_contracts import (
    CameraConfig,
    CameraSource,
    Flag,
    SyncEvent,
    SyncKind,
    SyncSource,
    Take,
    TakeCamera,
    TakeReport,
    TakeType,
    from_json,
    layout,
    to_json,
)

from mocap_capture import cli
from mocap_capture.report import ReportError, build_report, summary, write_report

T0 = 1_791_000_000_000_000_000
PERIOD = 33_333_333  # 30 fps
OK, NOT_OK = Flag.Value("FLAG_ON"), Flag.Value("FLAG_OFF")


def event(kind: str, ts: int) -> SyncEvent:
    return SyncEvent(kind=SyncKind.Value(f"SYNC_KIND_{kind}"), host_ts_ns=ts,
                     source=SyncSource.Value("SYNC_SOURCE_MANUAL"))


def camera(role: str) -> TakeCamera:
    return TakeCamera(config=CameraConfig(
        role=role, source=CameraSource.Value("CAMERA_SOURCE_STREAM"), width=1920, height=1080,
        fps=30, notes="", stream_host="10.0.0.1", video_port=1, sync_port=2, control_port=3,
        stats_port=4,
    ))


def frames(n=300, start=T0, jitter_ns=500_000, drop=(), seed=1):
    """(frame, host_ts_ns) at 30 fps with a little jitter; `drop` removes frame indexes."""
    rng = random.Random(seed)
    return [(i, start + i * PERIOD + rng.randint(-jitter_ns, jitter_ns))
            for i in range(n) if i not in drop]


def make_take(tmp_path, cams=None, start=T0 + 500_000_000, end=T0 + 9_000_000_000) -> Path:
    take_dir = tmp_path / "S1" / "takes" / "T1"
    layout.raw_dir(take_dir).mkdir(parents=True)
    cams = {"body_1": frames(seed=1), "body_2": frames(seed=2)} if cams is None else cams
    take = Take(id="T1", session_id="S1", type=TakeType.Value("TAKE_TYPE_PERFORMANCE"),
                start=event("START", start))
    if end is not None:
        take.end.CopyFrom(event("END", end))
    for role, rows in cams.items():
        take.cameras.append(camera(role))
        if rows is not None:
            lines = ["frame,host_ts_ns"] + [f"{f},{ts}" for f, ts in rows]
            layout.raw_timestamps(take_dir, role).write_text("\n".join(lines) + "\n")
    layout.take_json(take_dir).write_text(to_json(take))
    return take_dir


def test_good_take(tmp_path):
    report = build_report(make_take(tmp_path), max_gap_ms=100)
    assert report.ok == OK and list(report.problems) == []
    assert [c.role for c in report.reports] == ["body_1", "body_2"]
    cam = report.reports[0]
    assert cam.frames == 300
    assert cam.fps_measured == pytest.approx(30, abs=0.05)
    assert 0 < cam.fps_cv < 0.05
    assert list(cam.gaps) == []
    assert cam.first_ts_ns < report.reports[0].last_ts_ns


def test_short_gap_is_listed_but_ok(tmp_path):
    cams = {"body_1": frames(drop={100}, jitter_ns=0)}
    report = build_report(make_take(tmp_path, cams), max_gap_ms=100)
    assert report.ok == OK
    (gap,) = report.reports[0].gaps
    assert (gap.after_frame, gap.duration_ns) == (99, 2 * PERIOD)


def test_gap_longer_than_the_limit_fails(tmp_path):
    cams = {"body_1": frames(drop=set(range(100, 110)), jitter_ns=0)}
    report = build_report(make_take(tmp_path, cams), max_gap_ms=100)
    assert report.ok == NOT_OK
    assert report.problems[0].startswith("body_1: gap of 366.7 ms after frame 99 is longer than 100 ms")


def test_gap_uses_the_frame_numbers_of_the_file(tmp_path):
    rows = [(f + 5, ts) for f, ts in frames(n=10, jitter_ns=0, drop={4})]
    report = build_report(make_take(tmp_path, {"body_1": rows}, start=T0 + 100_000_000, end=T0 + 200_000_000), max_gap_ms=100)
    assert report.reports[0].gaps[0].after_frame == 8


@pytest.mark.parametrize(
    "start, end, message",
    [
        (T0 - 1, T0 + 9_000_000_000, "body_1: START {} is outside its range"),
        (T0 + 500_000_000, T0 + 299 * PERIOD + 10_000_000, "body_1: END {} is outside its range"),
    ],
)
def test_sync_event_outside_a_camera_range_fails(tmp_path, start, end, message):
    cams = {"body_1": frames(jitter_ns=0), "body_2": frames(start=T0 - 1_000_000, jitter_ns=0)}
    report = build_report(make_take(tmp_path, cams, start=start, end=end), max_gap_ms=100)
    assert report.ok == NOT_OK
    ts = start if "START" in message else end
    assert [p for p in report.problems if p.startswith("body_1")][0].startswith(message.format(ts))


def test_missing_end_fails(tmp_path):
    report = build_report(make_take(tmp_path, end=None), max_gap_ms=100)
    assert report.ok == NOT_OK
    assert "END is missing: the take never closed" in report.problems


def test_missing_or_empty_timestamps_fail(tmp_path):
    report = build_report(make_take(tmp_path, {"body_1": None, "body_2": []}), max_gap_ms=100)
    assert report.ok == NOT_OK
    assert list(report.problems) == [
        "body_1: body_1.timestamps.csv is missing", "body_1: no timestamps", "body_2: no timestamps",
    ]
    assert [c.frames for c in report.reports] == [0, 0]


def test_backwards_timestamps_and_bad_header(tmp_path):
    rows = frames(n=10, jitter_ns=0)
    rows[5], rows[6] = rows[6], rows[5]
    take_dir = make_take(tmp_path, {"body_1": rows, "body_2": frames(n=10)}, start=T0 + 100_000_000,
                         end=T0 + 200_000_000)
    layout.raw_timestamps(take_dir, "body_2").write_text("frame,ts\n0,1\n")
    problems = list(build_report(take_dir, max_gap_ms=100).problems)
    assert "body_1: host timestamps go backwards" in problems
    assert any(p.startswith("body_2: body_2.timestamps.csv has header ('frame', 'ts')") for p in problems)


def test_no_take_json_is_an_error(tmp_path):
    with pytest.raises(ReportError, match="take.json"):
        build_report(tmp_path, max_gap_ms=100)


def test_report_json_is_a_valid_contract_file(tmp_path):
    take_dir = make_take(tmp_path, end=None)
    written = write_report(take_dir, max_gap_ms=100)
    assert from_json(TakeReport, layout.report_json(take_dir).read_text()) == written


def test_summary(tmp_path):
    cams = {"body_1": frames(drop={100}, jitter_ns=0)}
    text = summary(build_report(make_take(tmp_path, cams, end=T0 + 20_000_000_000), max_gap_ms=100))
    assert text.splitlines()[0] == "take T1: NOT OK"
    assert "body_1: 299 frames, 29.90 fps" in text and "1 gap(s), longest 66.7 ms" in text
    assert "problem: body_1: END" in text


STREAM_CAMERA = {"role": "body_1", "source": "CAMERA_SOURCE_STREAM", "width": 1920,
                 "height": 1080, "fps": 30, "notes": "", "stream_host": "10.0.0.1",
                 "video_port": 1, "sync_port": 2, "control_port": 3, "stats_port": 4,
                 "preprocess": "none"}


def write_config(tmp_path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"storage": {"root": str(tmp_path)},
                                    "take": {"post_roll_ms": 0},
                                    "handoff": {"host": "127.0.0.1", "take_closed_port": 5600, "file_ready_port": 5601,
                        "ssh_user": "rafael", "data_root": "/data/mocap"},
                                    "report": {"max_gap_ms": 100}, "cameras": [STREAM_CAMERA]}))
    return path


@pytest.mark.parametrize("end, code", [(T0 + 9_000_000_000, 0), (None, 2)])
def test_cli_report(tmp_path, capsys, end, code):
    make_take(tmp_path, end=end)
    argv = ["report", "--config", str(write_config(tmp_path)), "--session", "S1", "--take", "T1"]
    assert cli.main(argv) == code
    assert capsys.readouterr().out.startswith("take T1: ")
    assert layout.report_json(tmp_path / "S1" / "takes" / "T1").exists()


def test_cli_report_unknown_take(tmp_path, capsys):
    argv = ["report", "--config", str(write_config(tmp_path)), "--session", "S1", "--take", "nope"]
    assert cli.main(argv) == 1
    assert "take.json" in capsys.readouterr().err
