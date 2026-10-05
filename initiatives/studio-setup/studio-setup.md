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

## Open decisions (Rafael, before the matching tasks start)

1. **Capture volume and camera placement:** size of the area the actors move in;
   position, height and aim of each body camera. Manual task cameras/1.
2. **Board:** squares (X×Y), square and marker size, ArUco dictionary, and the
   physical size/material (a board big enough for 4 body cameras at a distance
   is usually much bigger than A4; rigid backing so it stays flat).
   FreeMoCap's default board is the starting proposal. Declared in board/1.
3. **Face and hand cameras:** where are they mounted? If they're fixed in the
   room, they join the room calibration. If they move with the actor (helmet,
   wrist), they **can't** be calibrated with the room rig and need their own
   approach. This changes calibration-take and calibration-check.
4. **Where the quick check runs:** on the recorder (OpenCV-only, CPU, no neural
   nets: fits "simple operations"), or on the processing PC. Either way it calls
   `mocap-extract`'s calibration as a CLI, never imports it.
5. **Pass threshold** for the quick check (calibration reprojection error per
   camera, in pixels).

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
