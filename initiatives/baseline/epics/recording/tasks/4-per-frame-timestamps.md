## 4. Per-frame timestamps

- **Depends on:** 1
- **Contract:**
  - In: recorded file
  - Requires: `ffprobe -show_frames`
  - Delivers: `raw/<role>.timestamps.csv` (frame, pts_s)
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** short fixture
