# baseline — mocap-capture

**Goal:** P1 + P2: detect and configure cameras, record takes from USB (UVC) cameras and import takes from devices that record internally (tablets/standalone cameras), with flash sync and a verification report.

**Scope:** Linux; webcam via FFmpeg without re-encoding; Android tablets via `adb pull`; flash from mocap-sync-fw or manual. Camera sources sit behind an interface, so hardware can be swapped later without touching the rest.

**Out of scope:** ZMQ/Harpia control plane, tablet dashboard, remote recording trigger on the tablets (phase 2).

**Initiative gate:** A take with 1 webcam + ≥2 tablets produces valid `take.json` and `report.json` (contracts v0.1.0), with flashes detected on every camera.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
