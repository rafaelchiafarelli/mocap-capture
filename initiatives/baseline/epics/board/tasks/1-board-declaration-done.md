## 1. Board declaration

- **Depends on:** mocap-contracts `CalibrationBoard` (messages-v0/2); baseline bootstrap/1 (`load_config`)
- **Contract:**
  - In: `config.yaml`
  - Requires: a `board:` section filled into `CalibrationBoard` (squares_x, squares_y, square_length_mm, marker_length_mm, aruco_dictionary, measured_square_length_mm); validation rejects a missing or partial board; **no code anywhere has default board values**
  - Delivers: `load_config()` returns the board; the board is copied into `take.json` of every CALIBRATION take
- **Decisions:**
  - Rafael, 2026-10-12: FreeMoCap "5x3 Charuco", 55 mm squares, A4 (`mocap-studio/DEPENDENCIES.md`).
  - Claude, for Rafael's review: `board:` is optional in `config.yaml`, because a recorder that only records performances doesn't need one. A CALIBRATION take without it is refused before any camera starts. A partial board is always an error. `squares_x`, `squares_y` ≥ 2, lengths > 0, marker shorter than the square, and the dictionary is an OpenCV ArUco name (`DICT_4X4_250`).
  - Why now: moved from studio-setup into baseline for the MVP (`mocap-studio/MVP-plan.md`), whose calibration take needs it.
- **Pre-work:** done (board decided and printed)
- **Out of scope:** printing (task 2)
- **Tests:** valid board; each missing field rejected
