## 3. Take lifecycle (CLI)

- **Depends on:** 2 (START/END `SyncEvent`s, required by `Take`); devices/1, devices/5
- **Contract:**
  - In: session, take name, type
  - Requires: `config.yaml` `storage: {root}` (the recorder's data root, required, declared never guessed); creates `take_dir` via `layout` under it; builds every configured source through the `CameraSource` registry and checks it is ready (`prepare()`) before START; a configured kind with no registered source (e.g. UVC) is an error; writes `take.json`
  - Delivers: `mocap-capture take --session S --name N --type PERFORMANCE|CALIBRATION`
- **Pre-work:** none
- **Out of scope:** preprocessing and hand-off (epics `preprocess`, `handoff`)
- **Tests:** end-to-end fake take with fake sources
