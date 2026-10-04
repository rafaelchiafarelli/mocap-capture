## 1. TakeReport

- **Depends on:** recording/4; sync/2
- **Contract:**
  - In: take_dir
  - Requires: measured fps and coefficient of variation, gaps > 1.5 periods, START/END `SyncEvent`s present and inside every camera's timestamp range
  - Delivers: `report.json` (`TakeReport`) and a terminal summary; `ok=false` if a sync event is missing, falls outside a camera's range, or there is a large gap
- **Pre-work:** none
- **Out of scope:** visual detection of a sync marker in the video (only relevant if the LED flash comes back — `initiatives/future/README.md`)
- **Tests:** good and bad synthetic takes
