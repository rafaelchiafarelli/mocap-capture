# baseline — epics (execution order)

1. **bootstrap** — Skeleton (1 task)
2. **devices** — Camera sources (P1): UVC and STREAM (5 tasks)
3. **recording** — Recording (P2) (4 tasks)
4. **sync** — Sync markers on the host clock (2 tasks)
5. **verification** — Take report (P2.4) (1 task)
6. **preprocess** — Recorder-side crop/rescale after the take (2 tasks)
7. **handoff** — Per-file transfer + Harpia hand-off events to the processing PC (3 tasks)

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
