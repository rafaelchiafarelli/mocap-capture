## 3. Take lifecycle (CLI)

- **Depends on:** devices/1, devices/5
- **Contract:**
  - In: session, take name, type
  - Requires: creates `take_dir` via `layout`; builds every configured source through the `CameraSource` registry and checks it is ready (`prepare()`) before START; a configured kind with no registered source (e.g. UVC) is an error; writes `take.json`
  - Delivers: `mocap-capture take --session S --name N --type PERFORMANCE|CALIBRATION`
- **Pre-work:** none
- **Out of scope:** preprocessing and hand-off (epics `preprocess`, `handoff`)
- **Tests:** end-to-end fake take with fake sources
