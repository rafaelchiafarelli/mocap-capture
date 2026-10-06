## 2. Take integration

- **Depends on:** recording/2 (`ManualTrigger`), recording/3
- **Contract:**
  - In: —
  - Requires: START marker after every source has started; END marker before stopping
  - Delivers: `SyncEvent`s written to `take.json`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** event order in the fake take
