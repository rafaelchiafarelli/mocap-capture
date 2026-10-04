## 1. Flash detection in video

- **Depends on:** recording/4
- **Contract:**
  - In: video + timestamps
  - Requires: OpenCV; mean brightness per frame; peak above an adaptive threshold
  - Delivers: `detect_flashes(video) -> [frame]`
- **Pre-work:** Rafael records a short video with 2 flashes as a fixture
- **Out of scope:** —
- **Tests:** fixture: 2 flashes found
