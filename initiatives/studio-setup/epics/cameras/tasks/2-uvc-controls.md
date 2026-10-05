## 2. UVC camera controls (every V4L2 control)

- **Depends on:** baseline devices/4 (role → device); mocap-contracts v0.1.0 (`camera_control.harpia`)
- **Contract:**
  - In: a UVC device
  - Requires: `v4l2-ctl --list-ctrls-menus` / `--get-ctrl` / `--set-ctrl`. **Every** control the camera exposes is covered (brightness, contrast, saturation, gain, exposure and its auto mode, focus and auto focus, white balance and its auto mode, power-line frequency, …), never a fixed subset. Each control is read back after setting.
  - Delivers: `UvcControls.list(dev) -> [ControlCapability]` and `UvcControls.apply(dev, [ControlSetting]) -> [ControlResult]` (applied, clamped, unsupported, read-only or failed; never silently ignored)
- **Pre-work:** a `v4l2-ctl --list-ctrls-menus` fixture from the webcam in hand
- **Out of scope:** STREAM cameras (task 3); the CLI and take integration (task 4)
- **Tests:** the fixture parses into capabilities with ranges and menus; a rejected or clamped value is reported as such; an inactive control (e.g. manual exposure while auto is on) is reported, not hidden
