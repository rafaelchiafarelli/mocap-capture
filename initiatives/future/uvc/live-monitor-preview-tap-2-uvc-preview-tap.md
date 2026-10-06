## 2. UVC preview tap

- **Depends on:** 1; baseline recording/2 (`UvcSource`)
- **Contract:**
  - In: the running FFmpeg recording process of a UVC camera
  - Requires: the recording output stays `-c:v copy` to MKV, unchanged; a second, low-resolution output of the same FFmpeg process (e.g. MJPEG to a local pipe) feeds `PreviewTap`; if the preview consumer dies or stalls, recording continues
  - Delivers: `UvcSource` publishes preview frames for its role
- **Pre-work:** none
- **Out of scope:** streaming sources (task 3)
- **Tests:** fake FFmpeg with a stalled preview pipe: recording side unaffected
