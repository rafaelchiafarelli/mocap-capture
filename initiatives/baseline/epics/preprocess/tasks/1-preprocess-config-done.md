## 1. Preprocessing declaration

- **Depends on:** bootstrap; mocap-contracts v0.1.0 (`PreprocessSpec`)
- **Contract:**
  - In: `config.yaml`, `preprocess:` per role
  - Requires: every role declares its preprocessing explicitly: a `PreprocessSpec` (crop, output size) or `none`. A missing entry is an error, never a default.
  - Delivers: config validation that yields one `PreprocessSpec | None` per role
- **Pre-work:** none
- **Out of scope:** running it (task 2)
- **Tests:** valid spec, explicit `none`, missing role rejected, crop outside the source frame rejected
