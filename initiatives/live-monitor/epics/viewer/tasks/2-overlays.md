## 2. Overlays

- **Depends on:** 1; baseline recording/3 (take lifecycle)
- **Contract:**
  - In: `PreviewFrame`s, take state
  - Requires: the overlay list agreed in Open decision 4; frame age = host now − `host_ts_ns`
  - Delivers: role name, recording state + take name, live frame age, fps/drops warning per camera
- **Pre-work:** **Rafael confirms** the overlay list (live-monitor.md, Open decision 4)
- **Out of scope:** skeleton/pose overlays
- **Tests:** overlay values from a fake take and fake tap
