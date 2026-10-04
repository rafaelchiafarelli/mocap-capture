## 3. Take lifecycle (CLI)

- **Depends on:** 2; devices/5
- **Contract:**
  - In: session, take name, type
  - Requires: creates `take_dir` via `layout`; tells the operator to start the tablets; writes `take.json`
  - Delivers: `mocap-capture take --session S --name N --type PERFORMANCE|CALIBRATION`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** end-to-end fake take with fake sources
