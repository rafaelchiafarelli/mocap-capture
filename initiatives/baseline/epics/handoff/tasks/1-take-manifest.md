## 1. Take manifest

- **Depends on:** preprocess/2; verification/1
- **Contract:**
  - In: a finished take folder (after preprocessing and `report.json`)
  - Requires: `TakeManifest` from mocap-contracts; sha256 of every file that will be handed off
  - Delivers: `manifest.json`, written **last** and atomically (temp file + rename). Its presence means "complete and ready to hand off".
- **Pre-work:** **Rafael decides whether `raw/` is handed off too.** Proposal: no. Hand off `prep/` + `take.json` + `report.json`, and keep `raw/` on the recorder as the archive.
- **Out of scope:** copying (task 2)
- **Tests:** checksums match; a crash before the rename leaves no manifest
