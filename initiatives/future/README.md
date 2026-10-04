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
