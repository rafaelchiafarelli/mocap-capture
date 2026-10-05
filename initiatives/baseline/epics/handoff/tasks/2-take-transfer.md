## 2. Take transfer to the processing PC

- **Depends on:** 1
- **Contract:**
  - In: a take with `manifest.json`; `config.yaml` `handoff:` (processing PC host, data root). Declared, never discovered.
  - Requires: `rsync` over SSH; files are copied into the same `layout` path on the processing PC, and `manifest.json` goes **last**, so the far side never sees a half-copied take as ready
  - Delivers: `mocap-capture send --session S --take T`: resumable, and a rerun after success copies nothing
- **Pre-work:** SSH key access from the recorder to the processing PC; which network carries it (the capture Wi-Fi is busy during takes, so the proposal is the wired LAN)
- **Out of scope:** verifying on arrival (`mocap-extract` bootstrap/2); live streaming to the processing PC (phase 2)
- **Tests:** transfer to a local temp dir; an interrupted transfer resumes; the manifest arrives last
