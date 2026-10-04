# baseline — mocap-capture

**Goal:** P1 + P2: detect and configure cameras, record takes from USB (UVC) cameras and import takes from devices that record internally (tablets/standalone cameras), with all cameras on one host clock (per-frame timestamps + START/END sync markers) and a verification report.

**Scope:** Linux; webcam via FFmpeg without re-encoding; Android tablets via `adb pull`; sync markers are software events on the host clock (no sync hardware). Camera sources sit behind an interface, so hardware can be swapped later without touching the rest.

**Out of scope:** LED flash / any sync hardware (parked — `initiatives/future/README.md`); ZMQ/Harpia control plane, tablet dashboard, remote recording trigger on the tablets (phase 2).

**Initiative gate:** A take with 1 webcam + ≥2 tablets produces valid `take.json` and `report.json` (contracts v0.1.0), with START/END sync markers inside every camera's timestamp range.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
