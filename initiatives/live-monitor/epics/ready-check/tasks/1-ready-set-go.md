## 1. Ready-set-go

- **Depends on:** viewer epic (the operator needs to see every camera); baseline
  take lifecycle (`mocap-capture take`, START/END sync markers)
- **Contract:**
  - In: the take's configured body-camera roles; the live preview
  - Requires: a READY step before START. The operator confirms, per body
    camera, that the actor is fully in frame. START is refused until every
    body camera is confirmed, unless the operator overrides, and an override
    names the cameras and is recorded. GO = the moment START is accepted.
  - Delivers: `take.json` gets `ready` (per-camera confirmation time, or the
    override with its cameras) and the GO time on the recorder's host clock.
    Downstream metrics (detection rate) count frames **from GO**.
- **Pre-work:** a field name for `ready` in the take report. That's a
  `mocap-contracts` change (owner: mocap-capture, `capture.harpia`), its own
  small task, scoped before this one starts.
- **Out of scope:** automatic person detection on the recorder (no neural nets
  on the recorder PC); face and hand cameras (TBD).
- **Tests:** START refused with an unconfirmed camera; START accepted when all
  are confirmed; an override is recorded with its cameras; GO time in `take.json`.
