## 5. FILE_IMPORT source via adb

- **Depends on:** 1
- **Contract:**
  - In: tablet's adb serial
  - Requires: `adb` installed; files in DCIM
  - Delivers: `AdbImportSource.collect()` pulls the most recent video recorded after `host_start`, renames it to `<role>.mp4` in `raw/`
- **Pre-work:** Rafael confirms the folder where the tablets save video
- **Out of scope:** starting recording remotely
- **Tests:** mocked adb: picks the right file by date
