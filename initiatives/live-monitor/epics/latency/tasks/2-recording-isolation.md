## 2. Recording isolation

- **Depends on:** 1; baseline verification/1 (`TakeReport`)
- **Contract:**
  - In: two takes of the same setup, one with the monitor open, one without
  - Requires: `TakeReport` of both: same fps, no extra gaps or drops with the monitor open
  - Delivers: an automated check (fake sources) + the procedure for the real check; this is the initiative gate
- **Pre-work:** none for the automated check; the real check needs the cameras
- **Out of scope:** —
- **Tests:** fake sources with a deliberately slow viewer: `TakeReport` unchanged
