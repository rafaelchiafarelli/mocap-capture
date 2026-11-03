## 2. Images from upright tablets stream sideways

- **Symptom:** with a tablet upright, the image arrives rotated, because the
  sensor is landscape.
- **Where:** `mocap_capture/preprocess.py` has no rotation step.
- **Reproduce:** seen on 2026-10-12 in real takes with upright tablets.
- **Impact:** body detection and framing suffer unless the tablets are mounted in
  landscape, which is the workaround.
- **Likely fix:** a declared rotation per camera in the preprocessing step.
- **Status:** Open
