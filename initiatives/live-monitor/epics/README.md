# live-monitor — epics (execution order)

1. **preview-tap** — Latest frame per camera, without touching recording (3 tasks)
2. **viewer** — What the director sees (2 tasks)
3. **latency** — Prove it's live and harmless (2 tasks)

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
