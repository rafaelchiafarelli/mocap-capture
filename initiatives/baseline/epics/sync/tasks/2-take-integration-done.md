## 2. Take integration

- **Depends on:** recording/2 (`ManualTrigger`), recording/3
- **Contract:**
  - In: —
  - Requires: START marker after every source has started (a STREAM source's `start()` returns once its first frame is in); END marker before stopping
  - Implemented by the take lifecycle (recording/3); this task pins the order with tests
  - Delivers: `SyncEvent`s written to `take.json`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** event order in the fake take
