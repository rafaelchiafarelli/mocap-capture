# mocap-capture

Everything that happens **on the recorder PC**: setting up the studio (P1) and
recording takes (P2), up to handing each finished file to the processing PC.

## Where it sits in the architecture

```
UVC webcams (USB) ─────┐
                       ├──▶ mocap-capture ──rsync per file──▶ processing PC (mocap-extract)
STREAM tablets (Wi-Fi) ┘    on the recorder   └──Harpia ZeroMQ events: TakeClosed, CameraFileReady
  running mocap-camera-app
```

- **Cameras**, behind one `CameraSource` interface:
  - `UVC`: webcams through FFmpeg, recorded without re-encoding
  - `STREAM`: tablets running `mocap-camera-app`, received over stream
    protocol v1
- **Camera controls:** every control a camera offers can be listed and set,
  V4L2 for webcams and Camera2 for tablets. Values are read back from the
  device and recorded per take.
- **Recording:** one file per camera per take. Every frame is timestamped on
  the recorder's clock, and START/END sync markers are recorded too.
- **Take report:** frame counts, fps, gaps per camera.
- **Preprocessing:** crop and rescale per camera, CPU only, with no neural
  nets on this PC.
- **Hand-off:** each file is copied to the processing PC as soon as it's
  ready, then announced with a Harpia event. A sidecar JSON next to the file
  keeps the record if an event is lost.

It reads `config.yaml` (cameras, roles, controls, board, hand-off target) and
writes the take folder (`take.json`, `report.json`, `raw/`, `prep/`), all
defined in `mocap-contracts`.

## How it's used (planned)

```bash
mocap-capture camera controls --role body_1          # list every control the camera offers
mocap-capture camera set --role body_1 exposure_time_absolute=150
mocap-capture take --session S --name N --type CALIBRATION|PERFORMANCE
mocap-capture send --session S --take T              # resend anything missing
```

## Status

Planned, no code yet. It starts once `mocap-contracts` v0.1.0 is released.
Initiatives:
- [`baseline`](initiatives/baseline/baseline.md): cameras, recording, sync,
  report, preprocessing, hand-off
- [`studio-setup`](initiatives/studio-setup/studio-setup.md): checklist,
  ChArUco board, camera controls, guided calibration
- [`live-monitor`](initiatives/live-monitor/live-monitor.md): the director's
  live view
- [`future`](initiatives/future/README.md): parked ideas

Architecture: `mocap-studio/HANDOFF.md`. The recorder PC in detail
(components, one take step by step, the WSL2 development setup, build order):
[`docs/recorder-pc.drawio`](docs/recorder-pc.drawio).
