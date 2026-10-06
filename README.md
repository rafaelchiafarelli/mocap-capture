# mocap-capture

Everything that happens **on the recorder PC**: setting up the studio (P1) and
recording takes (P2), up to handing each finished file to the processing PC.

## Where it sits in the architecture

```
STREAM tablets (Wi-Fi) ──▶ mocap-capture ──rsync per file──▶ processing PC (mocap-extract)
  running mocap-camera-app   on the recorder  └──Harpia ZeroMQ events: TakeClosed, CameraFileReady
```

- **Cameras**, behind one `CameraSource` interface (a registry per source
  kind, so other image sources can be added):
  - `STREAM`: tablets running `mocap-camera-app`, received over stream
    protocol v1 and recorded without re-encoding
  - USB webcams (UVC) are not used; their tasks are parked in
    [`initiatives/future/uvc/`](initiatives/future/uvc/)
- **Camera controls:** every control a camera offers can be listed and set,
  Camera2 on the tablets. Values are read back from the
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
mocap-capture report --session S --take T          # rewrite and print report.json
mocap-capture send --session S --take T              # resend anything missing
```

## Development

```bash
make venv   # contracts submodule (stream v1 fixtures), .venv with Python 3.12, mocap-contracts v0.2.1, test extras
make test   # full suite
```

## config.yaml

Three sections so far. `storage.root` is the data root the session folders
live under (`<root>/<session>/takes/<take>/`), an absolute path.
`report.max_gap_ms` is the longest frame gap a take may have and still be ok
(shorter gaps are listed, not failed). `cameras` is
a list of `CameraConfig` entries from `mocap-contracts`. They're checked just like a contract file: only
declared fields, all required fields present, and the per-message rules (UVC
needs `device_hint`, STREAM needs a host and ports). Roles must be unique.
Any other top-level key is an error. Later sections (`handoff`, `board`, ...)
are added by the tasks that need them. Example:
[`tests/fixtures/config.yaml`](tests/fixtures/config.yaml).

## Status

Baseline in progress: bootstrap, devices (`CameraSource` registry, STREAM
source) and recording (`ManualTrigger`, `mocap-capture take`) done.
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
