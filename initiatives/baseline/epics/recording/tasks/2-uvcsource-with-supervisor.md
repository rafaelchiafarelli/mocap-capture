## 2. UvcSource with supervisor

- **Depends on:** 1
- **Contract:**
  - In: command
  - Requires: one process per camera; clean stop via `q` on stdin; crash detection
  - Delivers: `UvcSource` implementing `CameraSource`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** fake process: start/stop/crash
