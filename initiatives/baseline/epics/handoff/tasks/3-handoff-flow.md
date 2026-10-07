## 3. Hand-off flow (as soon as each file is ready)

- **Depends on:** 1; 2; recording/3; preprocess/2
- **Contract:**
  - In: a take that just hit END
  - Requires: per-file hand-off, never a take-level gate:
    1. At END: send `session.json` and `take.json`, then every role's `raw/<role>.timestamps.csv` with a `CameraFileReady` (TIMESTAMPS) for each, then publish `TakeClosed`. **`TakeClosed` means `session.json`, `take.json` and every timestamps file have arrived**, so the processing PC can resolve the take's actors and characters and align right away. `session.json` is needed because `take.json` refers to actors and characters by id (decision: Claude, for Rafael's review, 2026-10-05).
    2. As each role finishes preprocessing: send `prep/<role>.mkv`, then publish its `CameraFileReady` (VIDEO). Roles go independently, so a fast camera never waits for a slow one.
    3. `report.json` follows when it's ready (it doesn't gate processing).
  - Delivers: automatic hand-off at the end of `mocap-capture take`, plus `mocap-capture send --session S --take T` to resend anything missing (idempotent)
- **Pre-work:** none. **Decided 2026-10-06: `raw/` videos are not handed off.** They stay on the recorder as the archive. Timestamps always travel.
- **Out of scope:** live forwarding during the take (phase 2)
- **Tests:** with fakes: the order is session.json and take.json → timestamps → `TakeClosed` → videos per role; a slow role doesn't delay the others; the resend sends only what's missing
