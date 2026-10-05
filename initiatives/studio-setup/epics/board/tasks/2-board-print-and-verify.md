## 2. Board print and verify

- **Depends on:** 1
- **Contract:**
  - In: the declared board
  - Requires: OpenCV ArUco board generation; a PDF at exact physical scale (no "fit to page") with the parameters printed in the margin; after printing, Rafael measures a square with a caliper and that value goes into `measured_square_length_mm`, which is the one calibration uses
  - Delivers: `mocap-capture board pdf --out board.pdf`; checklist step "board printed and measured"
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** PDF page size and square size match the declaration
