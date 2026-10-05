# studio-setup — epics (execution order)

1. **procedure** — The session setup checklist (1 task)
2. **board** — Declare, print and verify the ChArUco board (2 tasks)
3. **cameras** — Placement and locked camera controls (3 tasks)
4. **calibration-take** — Guided calibration and ground-plane takes (2 tasks)
5. **calibration-check** — Pass/fail before the actors start (1 task)

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
