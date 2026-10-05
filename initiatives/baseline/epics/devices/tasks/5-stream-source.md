## 5. STREAM source

- **Depends on:** 1
- **Contract:**
  - In: `CameraConfig` with `source: STREAM` (stream_host, stream_port)
  - Requires: the camera app's stream protocol (H.264 over the network with each frame's capture time embedded in SEI; settings over HTTP `/control`), as measured in `mocap-studio/camera-stream-eval`; a clock-sync exchange before and after the take gives the device → host clock offset and drift
  - Delivers: `StreamSource`: `prepare()` connects and syncs clocks; `start(take)` writes the stream unchanged (no re-encode) to `raw/<role>.mkv`; `stop()` syncs clocks again; `raw/<role>.timestamps.csv` (frame, host_ts_ns) with every frame's capture time mapped onto the recorder's host clock (offset + linear drift)
- **Pre-work:**
  - The **production camera app** must exist, with its stream protocol written down. `camera-stream-eval`'s app is a decision tool, not the product. Building it is its own task/initiative (repo still to be decided, see `mocap-studio/HANDOFF.md`). It is not part of this task.
  - A short recorded H.264 fixture with SEI timestamps, committed (small) or fetched by a script
- **Out of scope:** locked camera controls (`studio-setup` cameras/3); live preview (`live-monitor` preview-tap/3); recording internally on the device
- **Tests:** the fixture produces the right frame count; with a synthetic offset and drift, host timestamps come out right; a stream that drops a connection gets flagged as a gap, never papered over
