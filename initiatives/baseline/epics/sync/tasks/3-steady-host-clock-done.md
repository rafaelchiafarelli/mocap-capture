## 3. Steady host clock

- **Depends on:** 2 (sync markers in the take), devices/5 (STREAM source)
- **Contract:**
  - In: —
  - Requires: every host time the recorder takes (clock-sync probes, frame arrival, START/END) from one clock that never steps
  - Delivers: `mocap_capture.clock.host_ns()`: Unix time in ns, anchored to the wall clock once per process and advanced by the monotonic clock. It's the default clock of `ManualTrigger`, `sync_clock` and `StreamSource`. The contracts are unchanged: host times are still Unix ns
- **Found 2026-10-12, first real take (bench-1):** WSL's wall clock (CLOCK_REALTIME) stepped **+2.94 s** in 30 s (WSL syncing with Windows). Sync offsets from the fastest probes then spread 200 ms to 2.9 s, and frames were stamped after they arrived. With the steady clock, a step in the wall clock can't move times within a take.
- **Decisions:** Claude, for Rafael's review: the absolute value can be off true wall time by whatever WSL corrects later. Nothing compares host times across processes or machines (every source in a take is stamped by the same recorder process), so only consistency within the process matters.
- **Also found:** WSL's clock itself runs **9.1 % slow** (Windows counted 22.5 s while WSL counted 20.6 s). The clocksource is `tsc`, mis-calibrated under Hyper-V on this i7-14700KF. Windows steps the wall clock forward to catch up; the monotonic clock just stays slow. This task removes the steps. The rate is fixed on the PC, outside this repository, by switching to `hyperv_clocksource_tsc_page` (runbook). Until then durations measure 9 % short and the tablets read ~32.6 fps.
- **Pre-work:** none
- **Out of scope:** the 32.6 fps the M7 streams at 1600×1200 (alignment resamples from real timestamps), the face camera's 4.3 s over-run past END (its own task)
- **Tests:** `host_ns` ignores a stepped wall clock; trigger, sync and source default to it
