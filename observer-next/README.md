# DJAEGER Observer Next

Observer-first validation build of DJAEGER AI.

- Stock kernel/governor remains the baseline.
- Legacy STABLE / SOFT_COOL / COOL / SAFE / RESPONSE / FREEZE presets are not installed.
- Observer reads CPU, GPU, thermal, battery/power, workload and frame state.
- The base sampler uses a 10-second interval outside registered games and a 3-second interval during a registered game. SurfaceFlinger sampling runs only for registered games.
- Gemini proposes a candidate inside the measured stock envelope. HERMES Local validates the exact candidate against kernel OPP, thermal and frame guards; ONE HERMES Cloud reviews that same candidate.
- A candidate can proceed only when all three candidate digests and confidence gates agree.
- Shadow evaluation is counterfactual: it compares naturally occurring stock samples that already fall inside the candidate envelope.
- No executor is packaged or started in v0.2.1. `EXECUTOR_ENABLED=0` remains hard-coded and there are no sysfs writes.
- Existing Hermes/Gemini API keys, IDs, tokens and cloud configuration are migrated locally and never logged or committed.
- Existing DJAEGER data is never deleted during migration.
- The Observer APK has a separate application ID and preserves the current Control Center Overview layout/order while publishing only Observer Next truth.

## Validation boundary

This release collects real-device evidence; it is not an automatic performance preset. A later executor release requires a separate review after enough independent frame and power windows pass, and must retain native thermal authority and verified readback/rollback controls.

## Workload registry

- `sts.al` (Arcane Legends) is the built-in game entry.
- Manual GAME entries enable frame learning, AI review and shadow evidence.
- Manual APP entries remain observational and are kept out of game semantics.
- A package cannot exist in both manual registries.
