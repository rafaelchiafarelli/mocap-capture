## 2. Preprocessing run (recorder, after the take)

- **Depends on:** 1; recording/3
- **Contract:**
  - In: `raw/<role>.mkv` + the role's `PreprocessSpec`
  - Requires: CPU only, no neural nets (the recorder's "simple operations" rule); FFmpeg crop/scale; **one output frame per input frame**, so no frame is dropped, duplicated or retimed
  - Delivers: `preprocess_role(take_dir, role)` → `prep/<role>.mkv`, run **per role** so each camera can be handed off as soon as it's done (handoff/3); `applied_preprocess` for the role written into `take.json`. A role declared `none` gets its stream copied without re-encoding. Timestamps stay in `raw/<role>.timestamps.csv` (frame count and timing don't change).
- **Pre-work:** **Rafael picks the output codec and quality.** Proposal: FFV1 (lossless), so nothing is lost before the neural nets, at a disk and transfer cost. Recorder "clean-up" operations beyond crop/scale aren't defined yet. Each one gets its own task once it's declared.
- **Out of scope:** anything that needs a neural net (processing PC)
- **Tests:** frame count and per-frame timing identical before and after; output size matches the spec; `none` is a byte copy of the stream
