# future — parked ideas

Not planned, not scheduled. Each entry becomes an initiative (through the
mocap-workflow planning process) only when there is a reason to pick it up.

## LED flash sync marker

A short, bright LED flash (ESP32 + MOSFET, firmware in `mocap-sync-fw`) fired at
the start and end of each take, visible to every camera, as a visual sync marker.

**Why parked:** the hardware isn't available, and the baseline syncs on the host
clock instead (per-frame timestamps + software START/END `SyncEvent`s). Revisit
only if the camera study shows timestamp sync isn't precise enough and a flash
gives a measured, clear improvement.

**What it would touch if revived:**
- `mocap-sync-fw`: the parked `flash` epic (PlatformIO skeleton, serial protocol, LED pulse).
- `mocap-capture`: a `FirmwareTrigger` next to `ManualTrigger` (sync epic);
  `detect_flashes(video) -> [frame]` (verification epic); flash frames in the `TakeReport`.
- `mocap-contracts`: `SyncEvent.source = FIRMWARE`, `CameraTakeReport.flash_frames`.
- `mocap-extract`: offsets/drift refined from the flash frames (alignment epic).

## UVC webcams

USB webcams recorded through FFmpeg (V4L2, MJPG, stream copy), stamped on the
host clock, with V4L2 controls and a low-res preview from the same FFmpeg
process.

**Why parked:** no webcam will be used. The cameras are tablets running
`mocap-camera-app` (STREAM). The `CameraSource` interface and its registry
(baseline devices/1) stay, so other image sources can be added; a UVC source
would be one of them.

**What it would touch if revived:** the task files in [`uvc/`](uvc/), written
and ready, named after where they came from:
- baseline devices/2 enumeration, /3 format probing, /4 role → device mapping
- baseline recording/1 FFmpeg command, /2 `UvcSource` with supervisor, /4 per-frame timestamps
- studio-setup cameras/2 UVC controls (and the "one interface over UVC + STREAM" in cameras/4)
- live-monitor preview-tap/2 UVC preview tap
- `config.yaml` already accepts `source: CAMERA_SOURCE_UVC` (`CameraConfig` in
  `mocap-contracts`); until a UVC source is registered, a take with one fails
  before START.
