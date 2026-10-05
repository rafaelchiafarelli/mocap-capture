## 2. Locked UVC controls

- **Depends on:** baseline devices/4 (role → device)
- **Contract:**
  - In: `controls:` per role in `config.yaml` (exposure, gain, focus, white balance, power-line frequency)
  - Requires: `v4l2-ctl --set-ctrl`; auto exposure/focus/white balance **off**; read back after setting and fail if the camera didn't take the value; applied before every take
  - Delivers: `apply_controls(dev, controls)`; the applied values written per role into `take.json`
- **Pre-work:** webcam `v4l2-ctl --list-ctrls` fixture
- **Out of scope:** streaming cameras (task 3)
- **Tests:** parsing and read-back on the fixture; a rejected value fails loudly
