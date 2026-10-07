"""The hand-off of one take, file by file, as soon as each file is ready.

    1. session.json, take.json, then every role's timestamps file with its
       CameraFileReady (TIMESTAMPS), then TakeClosed. TakeClosed means all of
       these have arrived, so the processing PC can align right away.
    2. Per role, independently: preprocess (if `prep/<role>.mkv` isn't there
       yet), send take.json again (it now has the role's applied_preprocess),
       then the video and its CameraFileReady (VIDEO). Preprocessing starts at
       once in parallel; sending waits for TakeClosed. So a VIDEO event means
       take.json with that role's applied_preprocess has arrived.
    3. report.json, which gates nothing.

For every file: the file, then its sidecar, then the event, so an event never
announces something the processing PC can't find. `raw/` videos stay on the
recorder (the archive). A missing session.json stops the hand-off before
anything is sent (preprocessing still runs); `mocap-capture send` finishes
it once the file is written. Rerunning is safe: rsync copies only what
differs, preprocessing is skipped when its output exists, and the processing
PC ignores duplicate events.
"""

from __future__ import annotations

import csv
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mocap_contracts import (
    CameraFileReady,
    ContractError,
    FileKind,
    Session,
    Take,
    TakeClosed,
    from_json,
    layout,
)

from mocap_capture import transfer
from mocap_capture.handoff import HandoffError, write_sidecar
from mocap_capture.preprocess import packet_count, preprocess_role, take_lock

TIMESTAMPS = FileKind.Value("FILE_KIND_TIMESTAMPS")
VIDEO = FileKind.Value("FILE_KIND_VIDEO")


def handoff_take(
    take_dir: Path,
    storage_root: Path,
    target: transfer.SshTarget | transfer.LocalTarget,
    publisher,
    *,
    report: Callable[[str], None] = print,
    preprocess: Callable[[Path, str], Path] | None = None,
) -> None:
    preprocess = preprocess or preprocess_role
    take = _read(Take, layout.take_json(take_dir))
    if not take.HasField("end"):
        raise HandoffError(f"take {take.id} never closed (no END in take.json); nothing sent")
    roles = [c.config.role for c in take.cameras]
    closed_sent = threading.Event()
    aborted = threading.Event()

    def role_flow(role: str) -> None:
        prep = take_dir / "prep" / f"{role}.mkv"
        if not prep.exists():
            preprocess(take_dir, role)
            report(f"{role}: preprocessed")
        while not closed_sent.wait(0.1):
            if aborted.is_set():
                return
        _send_take_json(take_dir, target)
        rel = f"prep/{role}.mkv"
        arrived = transfer.send_file(take_dir, rel, target, with_sidecar=False)
        first, last, _ = _span(take_dir, role)
        _announce(take_dir, target, publisher, CameraFileReady(
            take_id=take.id, role=role, kind=VIDEO, path=rel, size_bytes=arrived.size_bytes,
            sha256=arrived.sha256, frames=packet_count(prep), first_ts_ns=first, last_ts_ns=last,
        ))
        report(f"{role}: video handed off")

    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, len(roles))) as pool:
        futures = {role: pool.submit(role_flow, role) for role in roles}
        try:
            _closing_files(take, take_dir, storage_root, roles, target, publisher, report)
            closed_sent.set()
        except Exception as e:
            aborted.set()
            errors.append(str(e))
        for role, future in futures.items():
            try:
                future.result()
            except Exception as e:
                errors.append(f"{role}: {e}")

    if closed_sent.is_set() and layout.report_json(take_dir).exists():
        try:
            transfer.send_file(take_dir, "report.json", target)
        except transfer.TransferError as e:
            errors.append(f"report.json: {e}")
    if errors:
        raise HandoffError("hand-off incomplete (rerun mocap-capture send): " + "; ".join(errors))
    report(f"take {take.id} handed off")


def _closing_files(take, take_dir, storage_root, roles, target, publisher, report) -> None:
    session_path = layout.session_json(storage_root, take.session_id)
    if not session_path.is_file():
        raise HandoffError(f"{session_path} is missing; write it, then run mocap-capture send")
    session = _read(Session, session_path)
    if session.id != take.session_id:
        raise HandoffError(f"{session_path} is for session {session.id!r}, not {take.session_id!r}")
    transfer.send_session_file(storage_root, take.session_id, "session.json", target)
    _send_take_json(take_dir, target)
    for role in roles:
        rel = str(layout.raw_timestamps(take_dir, role).relative_to(take_dir))
        arrived = transfer.send_file(take_dir, rel, target, with_sidecar=False)
        first, last, frames = _span(take_dir, role)
        _announce(take_dir, target, publisher, CameraFileReady(
            take_id=take.id, role=role, kind=TIMESTAMPS, path=rel, size_bytes=arrived.size_bytes,
            sha256=arrived.sha256, frames=frames, first_ts_ns=first, last_ts_ns=last,
        ))
    closed = TakeClosed(take_id=take.id, start=take.start, end=take.end)
    closed.roles.extend(roles)
    _announce(take_dir, target, publisher, closed)
    report(f"take {take.id}: TakeClosed")


def _send_take_json(take_dir: Path, target) -> None:
    """take.json, never while preprocessing is rewriting it."""
    with take_lock(take_dir):
        transfer.send_file(take_dir, "take.json", target)


def _announce(take_dir: Path, target, publisher, event) -> None:
    """Sidecar written and delivered first, then the event."""
    sidecar = write_sidecar(take_dir, event)
    transfer.send_file(take_dir, str(sidecar.relative_to(take_dir)), target, with_sidecar=False)
    publisher.send(event)


def _span(take_dir: Path, role: str) -> tuple[int, int, int]:
    """(first_ts_ns, last_ts_ns, frames) of the role's timestamps file."""
    with open(layout.raw_timestamps(take_dir, role), newline="") as f:
        rows = list(csv.reader(f))[1:]
    if not rows:
        return 0, 0, 0
    return int(rows[0][1]), int(rows[-1][1]), len(rows)


def _read(cls, path: Path):
    try:
        return from_json(cls, path.read_text())
    except OSError as e:
        raise HandoffError(f"{path}: {e.strerror}") from None
    except ContractError as e:
        raise HandoffError(f"{path}: {e}") from None
