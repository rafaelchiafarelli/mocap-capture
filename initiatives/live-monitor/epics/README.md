# live-monitor — epics (execution order)

1. **preview-tap** — Latest frame per camera, without touching recording (2 tasks: 1, 3)
2. **viewer** — What the director sees (2 tasks)
3. **latency** — Prove it's live and harmless (2 tasks)

Task numbers have gaps where UVC tasks were parked (`initiatives/future/uvc/`).

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
