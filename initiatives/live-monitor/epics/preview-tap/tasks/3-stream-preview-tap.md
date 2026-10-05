## 3. Streaming-source preview tap

- **Depends on:** 1; **the streaming camera source** (not planned yet — architecture re-plan)
- **Contract:**
  - In: the H.264 stream a camera delivers to the recorder (capture time in SEI, as in `camera-stream-eval`)
  - Requires: decode on a separate thread from the one writing the file; decode as soon as a frame arrives (no player-style pacing — the `setpts=0` behaviour); drop frames if decode falls behind; `host_ts_ns` from the embedded capture time
  - Delivers: the streaming source publishes preview frames for its role
- **Pre-work:** the streaming source's own contract exists
- **Out of scope:** —
- **Tests:** recorded H.264 fixture with SEI timestamps; decoder slower than the stream: drops, never lags
