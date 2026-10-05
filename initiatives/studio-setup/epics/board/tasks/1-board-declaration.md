## 1. Board declaration

- **Depends on:** mocap-contracts `CalibrationBoard` (messages-v0/1); baseline bootstrap/1 (`load_config`)
- **Contract:**
  - In: `config.yaml`
  - Requires: a `board:` section filled into `CalibrationBoard` (squares_x, squares_y, square_length_mm, marker_length_mm, aruco_dictionary, measured_square_length_mm); validation rejects a missing or partial board; **no code anywhere has default board values**
  - Delivers: `load_config()` returns the board; the board is copied into `take.json` of every CALIBRATION take
- **Pre-work:** **Rafael decides** the board (studio-setup.md, Open decision 2)
- **Out of scope:** printing (task 2)
- **Tests:** valid board; each missing field rejected
