## 2. Sync markers

- **Depends on:** bootstrap
- **Contract:**
  - In: take start/stop from the take lifecycle (task 3, or a key press)
  - Requires: the host clock as Unix time in ns (`time.time_ns`, CLOCK_REALTIME: the clock stream protocol v1 maps every frame onto); the per-frame timestamps of every source share that clock (devices/5)
  - Delivers: `ManualTrigger.mark(kind)` returning `SyncEvent` (START/END, `host_ts_ns`, source MANUAL)
- **Pre-work:** none
- **Out of scope:** hardware sync markers (LED flash) — parked, see `initiatives/future/README.md`
- **Tests:** simulated input; event timestamps monotonic
