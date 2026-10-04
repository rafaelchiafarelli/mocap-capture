## 4. Role → device mapping

- **Depends on:** 2
- **Contract:**
  - In: config + devices
  - Requires: match by serial; fall back to `bus_path`; missing roles = error
  - Delivers: `resolve_roles(config, devices) -> {role: DeviceInfo}`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** serial, fallback, missing, duplicate
