## 3. STREAM camera controls (every Camera2 control)

- **Depends on:** the STREAM camera source (`baseline` devices/5); mocap-contracts camera-protocol camera-messages/3 (ZeroMQ channel); `mocap-camera-app` control/2, /3
- **Contract:**
  - In: a STREAM camera's role (its control endpoint is declared in `config.yaml`)
  - Requires: the app's `DeviceInfo` (every `ControlCapability`) and `ControlRequest` → `ControlReply` over the ZeroMQ channel, nothing else
  - Delivers: `StreamControls.list(role)` and `StreamControls.apply(role, [ControlSetting])`, returning `ControlResult`s with `applied` read back from the device. A device without manual control reports those controls as unsupported, never silently accepted.
- **Pre-work:** none
- **Out of scope:** the CLI and take integration (task 4)
- **Tests:** a fake app endpoint: list, apply, clamped and unsupported results; no reply within the timeout is an error
