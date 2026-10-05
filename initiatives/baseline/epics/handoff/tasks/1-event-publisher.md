## 1. Hand-off event publisher

- **Depends on:** bootstrap; mocap-contracts v0.1.0 (messages-v0/2, /6)
- **Contract:**
  - In: a `TakeClosed` or `CameraFileReady` message; `config.yaml` `handoff:` (processing PC event endpoint). Declared, never discovered.
  - Requires: the generated ZeroMQ sender from `mocap_contracts`
  - Delivers: `publish(event)`, which writes the event as its JSON sidecar (`closed.json` / `<file>.ready.json`, via `layout`) **and** sends it. The sidecar is written first and goes with the files, so the session folder stays the record even if a message is lost.
- **Pre-work:** none
- **Out of scope:** copying files (task 2); deciding when to publish (task 3)
- **Tests:** sidecar content == sent message; with the receiver down, the event still reaches it once it starts (critical delivery)
