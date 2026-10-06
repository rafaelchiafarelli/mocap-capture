"""START/END sync markers on the host clock.

The host clock is Unix time in ns (`time.time_ns`, CLOCK_REALTIME), the
clock every source's per-frame timestamps are on (stream protocol v1 maps
each frame onto it), so a marker can be placed inside every camera's range.

A trigger marks one START, then one END. A clock that steps back between
them (an NTP correction mid-take) is an error, never clamped.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from mocap_contracts import SyncEvent, SyncKind, SyncSource

START = SyncKind.Value("SYNC_KIND_START")
END = SyncKind.Value("SYNC_KIND_END")
MANUAL = SyncSource.Value("SYNC_SOURCE_MANUAL")


class SyncError(RuntimeError):
    """Markers out of order, or a host clock that went backwards."""


class ManualTrigger:
    """Markers set by the operator (or by the take lifecycle on their behalf)."""

    def __init__(self, clock: Callable[[], int] = time.time_ns):
        self._clock = clock
        self.start: SyncEvent | None = None
        self.end: SyncEvent | None = None

    def mark(self, kind: int) -> SyncEvent:
        if kind == START:
            if self.start is not None:
                raise SyncError("START is already marked")
            self.start = self._event(START)
            return self.start
        if kind == END:
            if self.start is None:
                raise SyncError("END before START")
            if self.end is not None:
                raise SyncError("END is already marked")
            end = self._event(END)
            if end.host_ts_ns < self.start.host_ts_ns:
                raise SyncError(
                    f"host clock went backwards: END {end.host_ts_ns} < START {self.start.host_ts_ns}"
                )
            self.end = end
            return self.end
        raise SyncError(f"can't mark {SyncKind.Name(kind)}")

    def mark_on_key(self, kind: int, prompt: str, read: Callable[[str], str] = input) -> SyncEvent:
        """Wait for the operator to press Enter, then mark."""
        read(prompt)
        return self.mark(kind)

    def _event(self, kind: int) -> SyncEvent:
        return SyncEvent(kind=kind, host_ts_ns=self._clock(), source=MANUAL)
