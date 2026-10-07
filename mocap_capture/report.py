"""The take report: what every camera delivered, and whether the take is usable.

Everything comes from the take folder: `take.json` (cameras, declared fps,
START/END) and each `raw/<role>.timestamps.csv`. Only the gap limit comes
from `config.yaml` (`report.max_gap_ms`).

Per camera: frames, first/last host time, measured fps ((frames - 1) / span),
fps_cv (std / mean of the frame intervals) and every gap longer than 1.5
periods of the declared fps. The take is ok only if START and END are present
and inside every camera's range, every camera has timestamps, and no gap is
longer than `max_gap_ms`. Shorter gaps are listed, not failed.
"""

from __future__ import annotations

import csv
import os
import statistics
from pathlib import Path

from mocap_contracts import (
    CameraTakeReport,
    ContractError,
    Flag,
    FrameGap,
    Take,
    TakeReport,
    from_json,
    layout,
    to_json,
)

GAP_PERIODS = 1.5


class ReportError(RuntimeError):
    """A take folder that can't be reported on at all."""


def build_report(take_dir: Path, max_gap_ms: float) -> TakeReport:
    path = layout.take_json(take_dir)
    try:
        take = from_json(Take, path.read_text())
    except OSError as e:
        raise ReportError(f"{path}: {e.strerror}") from None
    except ContractError as e:
        raise ReportError(f"{path}: {e}") from None

    report = TakeReport(take_id=take.id)
    problems: list[str] = []
    if not take.HasField("end"):
        problems.append("END is missing: the take never closed")
    for camera in take.cameras:
        role = camera.config.role
        rows = _timestamps(take_dir, role, problems)
        cam = _camera_report(role, rows, camera.config.fps, max_gap_ms, problems)
        report.reports.append(cam)
        if cam.frames == 0:
            continue
        for event, name in ((take.start, "START"), (take.end if take.HasField("end") else None, "END")):
            if event is not None and not cam.first_ts_ns <= event.host_ts_ns <= cam.last_ts_ns:
                problems.append(
                    f"{role}: {name} {event.host_ts_ns} is outside its range "
                    f"{cam.first_ts_ns}..{cam.last_ts_ns}"
                )
    report.problems.extend(problems)
    report.ok = Flag.Value("FLAG_OFF" if problems else "FLAG_ON")
    return report


def write_report(take_dir: Path, max_gap_ms: float) -> TakeReport:
    report = build_report(take_dir, max_gap_ms)
    path = layout.report_json(take_dir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(to_json(report))
    os.replace(tmp, path)
    return report


def summary(report: TakeReport) -> str:
    ok = report.ok == Flag.Value("FLAG_ON")
    lines = [f"take {report.take_id}: {'OK' if ok else 'NOT OK'}"]
    for cam in report.reports:
        longest = max((g.duration_ns for g in cam.gaps), default=0) / 1e6
        lines.append(
            f"  {cam.role}: {cam.frames} frames, {cam.fps_measured:.2f} fps "
            f"(cv {cam.fps_cv:.3f}), {len(cam.gaps)} gap(s)"
            + (f", longest {longest:.1f} ms" if cam.gaps else "")
        )
    lines += [f"  problem: {p}" for p in report.problems]
    return "\n".join(lines)


def _timestamps(take_dir: Path, role: str, problems: list[str]) -> list[tuple[int, int]]:
    path = layout.raw_timestamps(take_dir, role)
    try:
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = tuple(next(reader, ()))
            if header != layout.TIMESTAMPS_COLUMNS:
                problems.append(f"{role}: {path.name} has header {header}, expected {layout.TIMESTAMPS_COLUMNS}")
                return []
            rows = [(int(frame), int(ts)) for frame, ts in reader]
    except FileNotFoundError:
        problems.append(f"{role}: {path.name} is missing")
        return []
    except ValueError as e:
        problems.append(f"{role}: {path.name} is unreadable: {e}")
        return []
    if any(b[1] < a[1] for a, b in zip(rows, rows[1:])):
        problems.append(f"{role}: host timestamps go backwards")
    return rows


def _camera_report(
    role: str, rows: list[tuple[int, int]], fps: float, max_gap_ms: float, problems: list[str]
) -> CameraTakeReport:
    cam = CameraTakeReport(role=role, frames=len(rows))
    if not rows:
        problems.append(f"{role}: no timestamps")
        return cam
    cam.first_ts_ns, cam.last_ts_ns = rows[0][1], rows[-1][1]
    intervals = [b[1] - a[1] for a, b in zip(rows, rows[1:])]
    if intervals and cam.last_ts_ns > cam.first_ts_ns:
        cam.fps_measured = (len(rows) - 1) / ((cam.last_ts_ns - cam.first_ts_ns) / 1e9)
        mean = statistics.fmean(intervals)
        cam.fps_cv = statistics.pstdev(intervals) / mean if mean > 0 else 0.0
    limit_ns = GAP_PERIODS * 1e9 / fps
    for (frame, ts), interval in zip(rows, intervals):
        if interval > limit_ns:
            cam.gaps.append(FrameGap(after_frame=frame, duration_ns=interval))
            if interval > max_gap_ms * 1e6:
                problems.append(
                    f"{role}: gap of {interval / 1e6:.1f} ms after frame {frame} "
                    f"is longer than {max_gap_ms:g} ms"
                )
    return cam
