# baseline — mocap-capture

**Goal:** P1 + P2 on the **recorder PC**: detect and configure cameras, record takes from USB (UVC) cameras and from devices that stream live to the recorder (STREAM: tablets/phones running the camera app), with every camera on one host clock (per-frame timestamps + START/END sync markers). Then verify the take, preprocess it (crop/rescale, CPU only) and hand it off to the processing PC.

**Scope:** Linux; webcam via FFmpeg without re-encoding; STREAM devices' H.264 written without re-encoding, each frame's embedded capture time mapped onto the host clock; sync markers are software events on the host clock (no sync hardware); preprocessing limited to simple, CPU-only operations; hand-off file by file (rsync), each file announced to the processing PC by a Harpia event (`CameraFileReady` over ZeroMQ) as soon as it has arrived. Camera sources sit behind an interface, so hardware can be swapped later without touching the rest.

**Out of scope:** LED flash / any sync hardware (parked — `initiatives/future/README.md`); full studio setup and guided calibration (own initiative: `initiatives/studio-setup/`); live director monitor (own initiative: `initiatives/live-monitor/`); building the camera app itself (see `mocap-studio/HANDOFF.md`); devices that record internally (no `adb` import); anything that needs a neural net (processing PC); any Harpia control plane beyond the hand-off events (remote trigger, dashboard) and live forwarding to the processing PC (phase 2).

**Initiative gate:** A take with 1 webcam + ≥2 streaming tablets produces valid `take.json` and `report.json` (contracts v0.1.0), with START/END sync markers inside every camera's timestamp range; every file arrives intact on the processing PC, announced by its `CameraFileReady` event.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
