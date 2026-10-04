## 1. CameraSource interface

- **Depends on:** bootstrap
- **Contract:**
  - In: `CameraConfig`
  - Requires: Python Protocol with `prepare()`, `start(take)`, `stop()`, `collect(take_dir)`
  - Delivers: abstract `CameraSource` + registry keyed by the `CameraSource` enum
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** fake source satisfies the protocol
