## 1. Frame age measurement

- **Depends on:** viewer/1
- **Contract:**
  - In: a running monitor
  - Requires: log host now − `host_ts_ns` for every displayed frame, per role; summary min/median/p95/max
  - Delivers: `mocap-capture monitor --measure <seconds>` writing `monitor-latency.csv` and a summary
- **Pre-work:** **Rafael sets** the latency target (live-monitor.md, Open decision 3)
- **Out of scope:** screen scan-out latency (measured once by hand, e.g. filming a clock and the screen together)
- **Tests:** fake tap with known ages
