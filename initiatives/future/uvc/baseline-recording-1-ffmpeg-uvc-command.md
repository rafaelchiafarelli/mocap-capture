## 1. FFmpeg UVC command

- **Depends on:** devices
- **Contract:**
  - In: `CameraConfig` + format
  - Requires: `-f v4l2 -input_format mjpeg -c:v copy`, MKV, `-use_wallclock_as_timestamps 1`
  - Delivers: `build_ffmpeg_cmd(cfg, dev, out) -> list[str]`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** golden of the command
