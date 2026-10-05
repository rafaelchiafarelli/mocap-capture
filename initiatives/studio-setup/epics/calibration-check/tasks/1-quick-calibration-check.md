## 1. Quick calibration check

- **Depends on:** calibration-take/1; `mocap-extract` calibration/1 (as a CLI)
- **Contract:**
  - In: the calibration take just recorded
  - Requires: runs `mocap-extract`'s calibration through its CLI (no code import) on the machine from Open decision 4; reprojection error per camera vs the threshold from Open decision 5
  - Delivers: `mocap-capture calibration check <take>` → PASS/FAIL per camera, with the next action ("redo the take", "camera X moved?"); result saved in the session folder; checklist step "calibration passed"
- **Pre-work:** **Rafael decides** where it runs and the threshold (studio-setup.md, Open decisions 4–5)
- **Out of scope:** —
- **Tests:** fake CLI output: pass, fail, CLI error
