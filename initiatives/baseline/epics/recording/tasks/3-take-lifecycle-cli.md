## 3. Take lifecycle (CLI)

- **Depends on:** 2; devices/5
- **Contract:**
  - In: session, take name, type
  - Requires: creates `take_dir` via `layout`; checks that every configured source (UVC and STREAM) is ready before START; writes `take.json`
  - Delivers: `mocap-capture take --session S --name N --type PERFORMANCE|CALIBRATION`
- **Pre-work:** none
- **Out of scope:** preprocessing and hand-off (epics `preprocess`, `handoff`)
- **Tests:** end-to-end fake take with fake sources
