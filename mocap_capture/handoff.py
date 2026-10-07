"""Hand-off events to the processing PC (`mocap-extract watch`).

`publish` writes the event as its JSON sidecar first, then sends it:

    TakeClosed       → closed.json in the take folder
    CameraFileReady  → <file>.ready.json next to the file it announces

The sidecar travels with the files, so the session folder stays the record
and a lost message only delays the processing PC until it rescans. Sends are
PUSH sockets that connect to the endpoints declared in `config.yaml`
`handoff:`; ZeroMQ queues while the processing PC is down. On `close` the
queue gets `FLUSH_MS` to drain, then whatever is left is dropped (its sidecar
still has it).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import zmq
from mocap_contracts import CameraFileReady, TakeClosed, layout, to_json, transport

from mocap_capture.config import Handoff

FLUSH_MS = 2000


class HandoffError(RuntimeError):
    """An event that couldn't be recorded or queued."""


def sidecar_path(take_dir: Path, event: TakeClosed | CameraFileReady) -> Path:
    if isinstance(event, TakeClosed):
        return layout.closed_json(take_dir)
    if isinstance(event, CameraFileReady):
        return layout.ready_sidecar(take_dir / event.path)
    raise HandoffError(f"not a hand-off event: {type(event).__name__}")


def write_sidecar(take_dir: Path, event: TakeClosed | CameraFileReady) -> Path:
    """The event as JSON, written atomically (to_json also checks the contract)."""
    path = sidecar_path(take_dir, event)
    text = to_json(event)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
    return path


class Publisher:
    def __init__(self, handoff: Handoff, ctx: Any | None = None):
        self._ctx = ctx or zmq.Context.instance()
        self._senders = {
            TakeClosed: transport.new_sender(TakeClosed, self._ctx, handoff.take_closed_endpoint),
            CameraFileReady: transport.new_sender(
                CameraFileReady, self._ctx, handoff.file_ready_endpoint
            ),
        }

    def publish(self, take_dir: Path, event: TakeClosed | CameraFileReady) -> Path:
        """Write the sidecar, then send; returns the sidecar's path."""
        path = write_sidecar(take_dir, event)
        if not self._senders[type(event)].send(event):
            raise HandoffError(f"{type(event).__name__} not queued (sidecar written: {path})")
        return path

    def close(self, flush_ms: int = FLUSH_MS) -> None:
        for sender in self._senders.values():
            sender.socket.close(linger=flush_ms)

    def __enter__(self) -> Publisher:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
