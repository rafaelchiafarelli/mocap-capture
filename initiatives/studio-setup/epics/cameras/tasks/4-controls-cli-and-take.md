## 4. Camera controls: live CLI and take integration

- **Depends on:** 3
- **Contract:**
  - In: `config.yaml` `controls:` per role (any native key: value the device offers); the operator, live during setup
  - Requires: one controls interface, implemented for STREAM (task 3), so other sources can add theirs; nothing is applied unless declared in `config.yaml` or typed by the operator
  - Delivers:
    - `mocap-capture camera controls --role R` lists every control, with type, range, options and current value
    - `mocap-capture camera set --role R key=value …` sets controls live and prints each result
    - `mocap-capture camera save --role R` writes the current values into `config.yaml` `controls:`
    - Before every take, each role's declared controls are applied and read back. The take refuses to start if a declared control failed.
    - `take.json` gets `control_results` (full native record) and `applied_controls` (normalized `CameraControls` summary) per role
- **Pre-work:** none
- **Out of scope:** choosing the values (the setup checklist, `procedure/1`)
- **Tests:** a fake backend: list/set/save round trip; a declared control that fails blocks the take; `take.json` carries both records
