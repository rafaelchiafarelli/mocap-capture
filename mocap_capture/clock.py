"""The recorder's host clock: Unix time in ns that never steps.

WSL (and NTP anywhere) steps CLOCK_REALTIME: on 2026-10-12 it jumped +2.94 s in
30 s, which spread the stream clock-sync offsets over seconds and stamped
frames after they arrived. So every host time the recorder takes comes from
here: the wall clock read once per process, advanced by the monotonic clock.
Values are still Unix ns (the contracts say so); only their consistency within
one recorder process matters, and that holds whatever the wall clock does.
"""

import time

_ANCHOR_NS = time.time_ns() - time.monotonic_ns()


def host_ns() -> int:
    return _ANCHOR_NS + time.monotonic_ns()
