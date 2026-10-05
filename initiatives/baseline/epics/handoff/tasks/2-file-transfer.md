## 2. Per-file transfer to the processing PC

- **Depends on:** bootstrap
- **Contract:**
  - In: one file in a take folder (+ its sidecar, if any); `config.yaml` `handoff:` (processing PC host, data root)
  - Requires: `rsync` over SSH into the same `layout` path on the processing PC; written to a temporary name and renamed when complete, so no half-copied file is ever visible under its real name
  - Delivers: `send_file(take_dir, rel_path)`: resumable, and a rerun after success copies nothing; returns size and sha256 of what arrived
- **Pre-work:** SSH key access from the recorder to the processing PC; which network carries it (proposal: the wired LAN, since the capture Wi-Fi is busy during takes). The processing PC runs WSL2 behind NAT: Windows OpenSSH or a port forward into WSL, still to be decided.
- **Out of scope:** events (task 1); deciding what to send (task 3)
- **Tests:** transfer to a local temp dir; an interrupted transfer resumes; no file is visible under its final name before it's complete
