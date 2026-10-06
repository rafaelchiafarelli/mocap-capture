## 2. Post-roll after END

- **Depends on:** recording/3; 1 (the report checks END against every camera's range)
- **Contract:**
  - In: `config.yaml` `take: {post_roll_ms}` (required, declared never guessed)
  - Requires: after marking END, the take keeps every source recording for `post_roll_ms` before stopping. A STREAM frame reaches the recorder ~100 ms or more after it was captured, so without it the last recorded frame is captured before END and the report fails the take.
  - Delivers: END inside every camera's timestamp range on a real take; Ctrl+C during the post-roll stops at once (the report then says if END fell outside)
- **Pre-work:** none
- **Out of scope:** waiting for a frame past END per source (would add to the `CameraSource` interface; revisit if a fixed post-roll proves unreliable)
- **Tests:** fake take: stops happen ≥ post_roll_ms after END; END inside the range of fake sources that lag; Ctrl+C cuts the post-roll short
