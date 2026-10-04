## 3. Format probing

- **Depends on:** 2
- **Contract:**
  - In: `DeviceInfo`
  - Requires: parsing of `v4l2-ctl --list-formats-ext`
  - Delivers: `probe_formats(dev)`; `select_format(dev, w, h, fps, 'MJPG')` with a clear error if unavailable
- **Pre-work:** webcam `--list-formats-ext` fixture
- **Out of scope:** —
- **Tests:** parsing and selection on the fixture
