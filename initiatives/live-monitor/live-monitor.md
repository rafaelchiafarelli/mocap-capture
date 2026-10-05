# live-monitor — mocap-capture

**Goal:** Let the director watch every camera live, with no perceptible delay
(milliseconds, like `ffplay ... -vf setpts=0` on the streaming test), during
setup (framing the actors) and during takes.

**Scope:** A preview path on the recorder PC that takes the latest frame of each
camera and shows it right away. It never buffers to smooth playback, and it
**never slows down or drops a recorded frame**. Shows all roles, plus overlays
for take state and per-camera health.

**Out of scope:** Skeleton/pose overlays (that needs the neural nets on the
processing PC); remote control of the recording from the viewer; playback of
recorded takes; audio.

**Initiative gate:** With every configured camera recording, the viewer shows
all of them with p95 frame age ≤ the agreed target, and the recorded files are
identical in frame count and timestamps to a take recorded without the viewer
open.

**Blocked on:**
- The decisions listed under "Open decisions" below.
- The **STREAM camera source** (`baseline` devices/5), which is now planned, and the
  production camera app it needs (see `mocap-studio/HANDOFF.md`).

## Open decisions (Rafael, before any task starts)

1. **Where the director watches:** a window on the recorder PC's own screen, or
   a page served on the capture network for another device (laptop/tablet)?
   This decides the viewer epic, and whether the recorder needs to re-encode.
2. **Layout:** all cameras in a grid, or one large selected camera plus
   thumbnails? (7 cameras planned.)
3. **Latency target:** proposal p95 frame age ≤ 150 ms from capture to screen.
   The capture→PC part alone measured 45–60 ms median on the M7.
4. **Overlays:** proposal: role name, recording state + take name, live frame
   age, fps/drops warning per camera.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
