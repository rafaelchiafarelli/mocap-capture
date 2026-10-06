"""One take, from ready check to `take.json`.

    1. build every configured source (registry) and prepare() each one;
       any failure stops here, before anything is created
    2. create takes/<take>/ under storage.root, start every source,
       then mark START and write take.json (no end yet)
    3. record until the operator ends the take (Enter, or Ctrl+C)
    4. mark END, stop every source, collect their files, rewrite take.json
    5. write report.json (the take report) and print its summary

A source that fails to stop or collect doesn't keep the others from
stopping; the take is still closed and the failures are raised together.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from mocap_contracts import ContractError, Take, TakeCamera, TakeType, layout, to_json

import mocap_capture.stream  # noqa: F401  (registers the STREAM source)
from mocap_capture.config import Config
from mocap_capture.report import ReportError, summary, write_report
from mocap_capture.sources import CameraSource, create_source
from mocap_capture.sync import END, START, ManualTrigger

CALIBRATION = TakeType.Value("TAKE_TYPE_CALIBRATION")


class TakeError(RuntimeError):
    """A take that couldn't start, or closed with failures."""


def run_take(
    config: Config,
    session: str,
    name: str,
    take_type: int,
    *,
    wait_for_end: Callable[[], None],
    trigger: ManualTrigger | None = None,
    make_source: Callable = create_source,
    report: Callable[[str], None] = print,
) -> Path:
    """Run one take and return its folder. `wait_for_end` returns when the operator ends it."""
    trigger = trigger or ManualTrigger()
    try:
        take_dir = layout.take_dir(config.storage_root, session, name)
    except ContractError as e:
        raise TakeError(str(e)) from None
    if take_type == CALIBRATION:
        raise TakeError(
            "a CALIBRATION take needs the declared board (studio-setup board/1), not available yet"
        )
    if take_dir.exists():
        raise TakeError(f"{take_dir} already exists; a take is never overwritten")

    sources = _build(config, make_source)
    for source in sources:
        try:
            source.prepare()
        except Exception as e:
            raise TakeError(f"role {source.config.role} not ready: {e}") from None
        report(f"ready: {source.config.role}")

    take_dir.mkdir(parents=True)
    started: list[CameraSource] = []
    for source in sources:
        try:
            source.start(take_dir)
        except Exception as e:
            errors = _stop(started, report)
            raise TakeError(
                f"role {source.config.role} failed to start: {e}"
                + "".join(f"; {err}" for err in errors)
                + f" (no take.json; partial files left in {take_dir})"
            ) from None
        started.append(source)

    take = Take(id=name, session_id=session, type=take_type, start=trigger.mark(START))
    take.cameras.extend(TakeCamera(config=s.config) for s in sources)
    _write(take_dir, take)
    report(f"START {take.start.host_ts_ns}: recording {len(sources)} camera(s)")

    try:
        wait_for_end()
    except KeyboardInterrupt:
        pass
    take.end.CopyFrom(trigger.mark(END))
    report(f"END {take.end.host_ts_ns}")

    errors = _stop(sources, report)
    for source in sources:
        try:
            files = source.collect(take_dir)
        except Exception as e:
            errors.append(f"role {source.config.role} failed to collect: {e}")
            continue
        report(f"{source.config.role}: " + ", ".join(str(f.relative_to(take_dir)) for f in files))
        for problem in getattr(source, "problems", []):
            report(f"{source.config.role}: {problem}")
    _write(take_dir, take)
    report(f"wrote {layout.take_json(take_dir)}")
    try:
        report(summary(write_report(take_dir, config.max_gap_ms)))
    except ReportError as e:
        errors.append(f"no report: {e}")
    if errors:
        raise TakeError("take closed with failures: " + "; ".join(errors))
    return take_dir


def _build(config: Config, make_source: Callable) -> list[CameraSource]:
    sources = []
    for camera in config.cameras:
        try:
            sources.append(make_source(camera))
        except LookupError as e:
            raise TakeError(str(e)) from None
    return sources


def _stop(sources: list[CameraSource], report: Callable[[str], None]) -> list[str]:
    errors = []
    for source in sources:
        try:
            source.stop()
        except Exception as e:
            errors.append(f"role {source.config.role} failed to stop: {e}")
            report(errors[-1])
    return errors


def _write(take_dir: Path, take: Take) -> None:
    path = layout.take_json(take_dir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(to_json(take))
    os.replace(tmp, path)
