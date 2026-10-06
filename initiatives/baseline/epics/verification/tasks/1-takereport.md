## 1. TakeReport

- **Depends on:** devices/5 (timestamps); sync/2
- **Contract:**
  - In: take_dir
  - Requires: per camera, from `raw/<role>.timestamps.csv`: frames, first/last `host_ts_ns`, measured fps ((frames − 1) / span), `fps_cv` (std / mean of the frame intervals), every gap > 1.5 periods of the **declared** fps as a `FrameGap`; START/END `SyncEvent`s from `take.json` present and inside every camera's timestamp range; `config.yaml` `report: {max_gap_ms}` (required, declared never guessed)
  - Delivers: `report.json` (`TakeReport`) and a terminal summary; `ok=false` if a sync event is missing, falls outside a camera's range, a camera has no timestamps, or a gap is longer than `max_gap_ms` (shorter gaps are listed, not failed). `mocap-capture take` writes it when the take closes; `mocap-capture report --session S --take T` rewrites it
- **Pre-work:** none
- **Out of scope:** visual detection of a sync marker in the video (only relevant if the LED flash comes back — `initiatives/future/README.md`)
- **Tests:** good and bad synthetic takes
