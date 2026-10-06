## 1. CameraSource interface

- **Depends on:** bootstrap
- **Contract:**
  - In: `CameraConfig`
  - Requires: Python Protocol with `config: CameraConfig`, `prepare()`, `start(take_dir: Path)`, `stop()`,
    `collect(take_dir: Path) -> list[Path]` (the files it wrote under `raw/`, per `layout`)
  - Delivers: abstract `CameraSource` + registry keyed by the `CameraSource` enum
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** fake source satisfies the protocol
