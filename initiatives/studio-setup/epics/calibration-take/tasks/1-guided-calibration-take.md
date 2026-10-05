## 1. Guided calibration take

- **Depends on:** board/1; live-monitor preview-tap/1; baseline recording/3 (take lifecycle)
- **Contract:**
  - In: a CALIBRATION take while it records; the declared board
  - Requires: ChArUco detection on the **preview** frames (never on the recording path); per camera: frames with the board seen, a coverage map of where in the image it was seen, and for each camera pair the frames where both see it; the operator sees it live and stops when every camera reaches the target
  - Delivers: `mocap-capture take --type CALIBRATION --guided`; coverage summary saved with the take
- **Pre-work:** **Rafael decides** face/hand camera mounting (studio-setup.md, Open decision 3); coverage targets proposed in the task, confirmed by Rafael
- **Out of scope:** solving the calibration (calibration-check)
- **Tests:** recorded fixture frames with the board: detections and coverage counted
