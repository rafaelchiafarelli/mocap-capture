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
- The open decision on layout (2) for the viewer epic.
- The **STREAM camera source** (`baseline` devices/5), which is now planned, and the
  production camera app (`mocap-camera-app`) it reads from.

## Decisions (Rafael, 2026-10-12) and what is still open

1. **Where the director watches: decided.** On the **recorder PC's own screen**.
   No network viewer, no re-encoding.
2. **Layout: open, and it must be switchable.** Rafael expects a many-camera
   setup whose layout may change. Candidate layouts (selected camera +
   thumbnails, equal grid, spatial/top-down map, …) are being compared before
   the viewer epic starts. Whatever is chosen, the layout is a config/runtime
   choice, not hard-wired.
3. **Latency target: proposal stands** (p95 frame age ≤ 150 ms), not yet
   confirmed.
4. **Overlays: none for now.** Start with plain images and add overlays only
   when a need appears.
5. **Ready-set-go before every take: decided.** Before START, the operator
   confirms on the monitor that the actor is in frame on each body camera.
   Detection-rate metrics count from GO, because the actor may not be on screen
   when recording starts. See epic `ready-check`.

General context, cross-repository order and open questions:
`mocap-studio/HANDOFF.md`.
