## 2. Per-file transfer to the processing PC

- **Depends on:** bootstrap
- **Contract:**
  - In: one file in a take folder (+ its sidecar, if any); `config.yaml` `handoff:` (processing PC host, data root)
  - Requires: `rsync` over SSH into the same `layout` path on the processing PC; written to a temporary name and renamed when complete, so no half-copied file is ever visible under its real name
  - Delivers: `send_file(take_dir, rel_path)`: resumable, and a rerun after success copies nothing; returns size and sha256 of what arrived
- **Pre-work:** none for the code (tested against a local folder). **Network decided 2026-10-06: the wired LAN** (the capture Wi-Fi is busy during takes), with **WSL2 `networkingMode=mirrored`** on the processing PC and `sshd` inside WSL, so rsync and the ZeroMQ events reach WSL on the Windows LAN IP with no port forward (needs Windows 11 22H2+). For a real transfer, Rafael sets up the recorder's SSH key on the processing PC.
- **Out of scope:** events (task 1); deciding what to send (task 3)
- **Tests:** transfer to a local temp dir; an interrupted transfer resumes; no file is visible under its final name before it's complete
