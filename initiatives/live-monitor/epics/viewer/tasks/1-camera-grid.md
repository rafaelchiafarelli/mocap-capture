## 1. Camera layouts

- **Depends on:** preview-tap/1
- **Contract:**
  - In: `PreviewTap`, roles from `config.yaml`
  - Requires: on the recorder PC's own screen (decision 1); the four layouts of decision 2 (A grid, B selected + strip, C room map, D selected + room map), switchable at runtime with a keypress, default from `config.yaml`; a selected camera for B/D, switchable by clicking a feed or a key; room-map positions from each role's declared side (`n`/`e`/`s`/`w`, or a corner for face/hands) in `config.yaml`; portrait feeds letterboxed, never cropped; redraw from `latest()` at display rate; a camera with no recent frame shows as stale, never frozen silently
  - Delivers: `mocap-capture monitor [--layout A|B|C|D]` showing every role
- **Pre-work:** done (decisions 1–2, 2026-10-12). Needs a `side` field per role in the config schema: declared in this task's contract, added to `config.yaml` validation here
- **Out of scope:** overlays (task 2)
- **Tests:** fake tap with N roles; each layout places every role; C/D place roles by declared side; a role without a side fails validation for C/D; switching layout keeps the selected camera; stale detection
