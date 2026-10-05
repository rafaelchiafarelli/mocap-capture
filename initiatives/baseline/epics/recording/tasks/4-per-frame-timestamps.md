## 4. Per-frame timestamps (UVC)

- **Depends on:** 1
- **Contract:**
  - In: a UVC recording (FFmpeg with wall-clock timestamps)
  - Requires: `ffprobe -show_frames`
  - Delivers: `raw/<role>.timestamps.csv` (frame, host_ts_ns): the same format the STREAM source writes (devices/5), on the recorder's host clock
- **Pre-work:** none
- **Out of scope:** STREAM sources (they write their own, devices/5)
- **Tests:** short fixture
