## 1. The WSL clock runs 9.1 % slow on the processing PC

- **Symptom:** takes measure 9 % short, and tablets read 32.6 fps instead of 30.
  Windows steps the wall clock to catch up.
- **Where:** the machine, not the code. The clocksource `tsc` is mis-calibrated
  under Hyper-V on the i7-14700KF. `mocap_capture/clock.py` holds the steady clock
  (baseline sync/3), which removes the steps but not the wrong rate.
- **Reproduce:** seen on 2026-10-12 in real takes. On 2026-11-03,
  `/sys/devices/system/clocksource/clocksource0/current_clocksource` still reads `tsc`.
- **Impact:** every take recorded in WSL on this PC has the wrong duration and fps.
- **Likely fix:** needs Rafael's `sudo`:
  `echo hyperv_clocksource_tsc_page | sudo tee /sys/devices/system/clocksource/clocksource0/current_clocksource`,
  and permanently `kernelCommandLine = clocksource=hyperv_clocksource_tsc_page` under
  `[wsl2]` in `C:\Users\rafae\.wslconfig`.
- **Status:** Open
