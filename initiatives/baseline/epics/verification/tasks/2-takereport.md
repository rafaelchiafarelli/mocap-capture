## 2. TakeReport

- **Depends on:** 1
- **Contract:**
  - In: take_dir
  - Requires: measured fps and coefficient of variation, gaps > 1.5 periods, flashes per camera
  - Delivers: `report.json` (`TakeReport`) and a terminal summary; `ok=false` if a flash is missing or there is a large gap
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** good and bad synthetic takes
