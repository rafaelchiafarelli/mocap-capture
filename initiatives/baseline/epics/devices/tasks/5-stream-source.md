## 5. STREAM source

- **Depends on:** 1; `mocap-contracts` camera-protocol stream-protocol/1, /2 (stream protocol v1 spec + fixtures + reference reader)
- **Contract:**
  - In: `CameraConfig` with `source: STREAM` (`stream_host`, `video_port`, `sync_port`)
  - Requires: **stream protocol v1** (`mocap-contracts`): H.264 with each frame's capture time in SEI, and the clock-sync exchange before and after the take that gives the device → host clock offset and drift. Tested against v1's fixtures.
  - Delivers: `StreamSource`: `prepare()` connects and syncs clocks; `start(take)` writes the stream unchanged (no re-encode) to `raw/<role>.mkv`; `stop()` syncs clocks again; `raw/<role>.timestamps.csv` (frame, host_ts_ns) with every frame's capture time mapped onto the recorder's host clock (offset + linear drift)
- **Pre-work:**
  - None for the code: the v1 fixtures come from `mocap-contracts`. For a live end-to-end check, a tablet running a v1 app (`mocap-camera-app` streaming/1, or the eval app if v1 keeps its format).
- **Out of scope:** the app's settings and control channel (`mocap-camera-app`, over Harpia ZeroMQ); locked camera controls (`studio-setup` cameras/3); live preview (`live-monitor` preview-tap/3); recording internally on the device
- **Tests:** the fixture produces the right frame count; with a synthetic offset and drift, host timestamps come out right; a stream that drops a connection gets flagged as a gap, never papered over
