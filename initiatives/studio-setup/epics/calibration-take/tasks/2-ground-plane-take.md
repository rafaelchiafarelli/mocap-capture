## 2. Ground-plane take

- **Depends on:** 1
- **Contract:**
  - In: the board lying flat on the floor at the chosen origin
  - Requires: a short take where the board is still and seen by enough body cameras; the operator gets a live "seen by N cameras" check; the floor origin is marked so it can be repeated
  - Delivers: the ground-plane frames `mocap-extract/calibration/2` needs, tagged in `take.json`
- **Pre-work:** none
- **Out of scope:** computing the floor transform (mocap-extract)
- **Tests:** fake detections: enough / not enough cameras
