# studio-setup — mocap-capture

**Goal:** P1, done properly: everything that has to be right **before** the actors
perform. That means the studio and cameras set up, the ChArUco board declared and
printed, camera settings locked, a calibration take recorded with live guidance,
and the calibration checked as good **before** anyone says "action".

**Scope:** The setup procedure (checklist), the calibration board declaration,
printing and verification, camera placement and locked camera controls, guided
calibration and ground-plane takes, and a quick calibration check with a pass/fail
answer during the session.

**Out of scope:** The calibration math itself (`mocap-extract/calibration`, reused
by the quick check, never copied); recording performance takes (baseline); the
director's view (`live-monitor`, which this initiative reuses for framing).

**Initiative gate:** Starting from an empty room, following the checklist
produces a session with a declared board, locked camera settings recorded in
`take.json`, and a calibration that passes the quick check, all before the first
performance take.

## Decisions (Rafael, 2026-10-12) and what is still open

1. **Capture volume and camera placement: decided.** About a 3 m × 3 m × 3 m
   cube, with **one body camera per side** (4). These numbers are **config
   values, never constants in code**: the volume and the room change. More than
   one recording location is expected, so **calibration is per location and per
   session**, and recalibrating must be cheap and routine. Exact positions,
   heights and aim are still the manual task cameras/1.
2. **Board: decided.** FreeMoCap's **"5x3 Charuco"** (the only other board
   FreeMoCap 1.8.2 supports is 7x5): 5 × 3 squares, `DICT_4X4_250`,
   **square 200 mm, marker 160 mm**, printed on **A0 landscape at 100 %**,
   mounted on a rigid, flat, matte backing (5 mm foam board or 3 mm ACM).
   Print file: `/mnt/g/mocap-studio-downloads/calibration/charuco-5x3-200mm-A0.pdf`
   (with a 100 mm scale bar to check the print). After printing, a caliper
   measurement of a square goes into `measured_square_length_mm`.
   Why 5x3/200 mm: the tablets stream a soft 1600×1200 image, and the far
   corner of the volume is ~4 m away, so the squares must be large. A synthetic
   detection test (blur, noise, 0–30 % tilt) found all 8 corners from ~40 to
   ~80 px per square. board/2 confirms it with real tablet frames.
3. **Face and hand cameras: partly open.** Hand cameras are **TBD**: their tasks
   wait. A face camera is likely, but whether it's fixed in the room or worn is
   still being researched by Rafael. Plan the room calibration for the four body
   cameras first.
4. **Where the quick check runs: open.**
5. **Pass threshold: decided as a rule, not a pixel constant.** Calibration has
   to be good to **1 cm**, or there's no point continuing. So:
   - per-camera reprojection error must be below **the pixel size of 1 cm at the
     farthest working distance** (`10 mm × focal_px / max_distance`, from the
     calibration and the configured volume), and
   - a known-geometry check: the triangulated distance between board corners
     must match the board within **10 mm**.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
