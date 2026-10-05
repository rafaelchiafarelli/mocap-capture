## 1. PreviewTap interface

- **Depends on:** baseline devices/1 (`CameraSource`)
- **Contract:**
  - In: role
  - Requires: one slot per role holding only the **latest** decoded frame + its capture time on the host clock (`host_ts_ns`); writers overwrite, never queue; readers never block writers
  - Delivers: `PreviewTap.publish(role, frame, host_ts_ns)` / `PreviewTap.latest(role) -> PreviewFrame | None`; frame = BGR `numpy` array at preview resolution
- **Pre-work:** none
- **Out of scope:** decoding, display
- **Tests:** a slow reader only ever sees the newest frame; writer timing unaffected by a stalled reader
