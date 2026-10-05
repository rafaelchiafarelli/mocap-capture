## 3. Locked streaming-camera controls

- **Depends on:** the STREAM camera source (`baseline` devices/5); `mocap-camera-app` control/2 (manual controls over the ZeroMQ channel)
- **Contract:**
  - In: same `controls:` section as task 2
  - Requires: the camera app accepts locked exposure/ISO/focus/white balance as a `ControlRequest` (`camera.harpia`, over Harpia ZeroMQ) and reports what it actually applied; devices without manual control are flagged, not silently accepted
  - Delivers: controls applied and recorded in `take.json`, same as task 2
- **Pre-work:** check which manual controls each tablet's Camera2 hardware level allows
- **Out of scope:** —
- **Tests:** fake control API; unsupported control flagged
