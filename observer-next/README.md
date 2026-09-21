# DJAEGER Observer Next

Observer-first rebuild of DJAEGER AI.

- Stock kernel/governor remains the baseline.
- Legacy STABLE / SOFT_COOL / COOL / SAFE / RESPONSE / FREEZE presets are not installed.
- Observer reads CPU, GPU, thermal, battery/power and workload state.
- Hermes Local, Hermes Cloud and Gemini consume one normalized observation contract.
- AI produces structured policy only; privileged writes are handled by a validated local executor.
- Existing Hermes/Gemini API keys, IDs, tokens and cloud configuration are migrated locally and never logged or committed.
- Existing DJAEGER data is never deleted during migration.
- APK Overview card order remains: STATUS -> THOUGHT -> HERMES -> CTX1 -> STRATEGY -> OUTCOME LEARNING.
