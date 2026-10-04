## 2. UVC enumeration

- **Depends on:** 1
- **Contract:**
  - In: —
  - Requires: `pyudev` or `v4l2-ctl`
  - Delivers: `list_uvc_devices() -> [DeviceInfo(path, name, serial, bus_path)]`
- **Pre-work:** Rafael saves the webcam's `v4l2-ctl --list-devices` output to `tests/fixtures/`
- **Out of scope:** —
- **Tests:** fixture parsing
