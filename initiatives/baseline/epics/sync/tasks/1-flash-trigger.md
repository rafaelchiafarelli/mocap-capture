## 1. Flash trigger

- **Depends on:** bootstrap
- **Contract:**
  - In: serial port or nothing
  - Requires: mocap-sync-fw protocol (`FLASH`, `PING`); manual fallback via key press
  - Delivers: `FirmwareTrigger.flash()` and `ManualTrigger.flash()` returning `SyncEvent`
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** fake serial; manual with simulated input
