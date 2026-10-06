# baseline — epics (execution order)

1. **bootstrap** — Skeleton (1 task)
2. **devices** — Camera sources (P1): the `CameraSource` interface and the STREAM source (2 tasks: 1, 5)
3. **recording** — Sync markers and the take lifecycle (P2) (2 tasks: 2, 3)
4. **sync** — START/END in the take, checked (1 task: 2; sync markers moved to recording/2)
5. **verification** — Take report (P2.4) (1 task)
6. **preprocess** — Recorder-side crop/rescale after the take (2 tasks)
7. **handoff** — Per-file transfer + Harpia hand-off events to the processing PC (3 tasks)

Task numbers have gaps where UVC tasks were parked (`initiatives/future/uvc/`).

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green.
