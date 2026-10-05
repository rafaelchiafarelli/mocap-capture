## 1. Camera grid

- **Depends on:** preview-tap/1
- **Contract:**
  - In: `PreviewTap`, roles from `config.yaml`
  - Requires: layout and display target from Open decisions 1–2; redraw from `latest()` at display rate; a camera with no recent frame shows as stale, never frozen silently
  - Delivers: `mocap-capture monitor` showing every role
- **Pre-work:** **Rafael decides** where the director watches and the layout (live-monitor.md, Open decisions 1–2)
- **Out of scope:** overlays (task 2)
- **Tests:** fake tap with N roles; stale detection
