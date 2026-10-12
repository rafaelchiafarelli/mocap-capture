## 2. Overlays

- **Depends on:** 1; baseline recording/3 (take lifecycle)
- **Contract:**
  - In: `PreviewFrame`s, take state
  - Requires: the overlay list agreed in Open decision 4; frame age = host now − `host_ts_ns`
  - Delivers: role name, recording state + take name, live frame age, fps/drops warning per camera
- **Pre-work:** **deferred**: no overlays for now (live-monitor.md, decision 4, 2026-10-12). Only the role name is shown, by task 1. Revisit when a need appears
- **Out of scope:** skeleton/pose overlays
- **Tests:** overlay values from a fake take and fake tap
