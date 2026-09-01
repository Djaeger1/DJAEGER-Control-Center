# r78 implementation plan

## Reader layer
Create one coherent privileged read operation for `/data/adb/djaeger_ai/cc_snapshot`, `runtime_status`, `root_authority_state`, strategy formula/result, Gemini HTTP/resync/server state, and masked vault status. Parse key/value files as inert data; never source shell content.

## Model layer
Keep separate models for Runtime, Telemetry, Brain/LocalAI, StrategyFormula, StrategyResult, GeminiTransport, RootAuthority, Learning, Network and KeyVault. Attach source timestamp/freshness to every model.

## UI
Add a Strategy Composition card/page showing concrete module-published CPU LITTLE/BIG, GPU, governors, power/burst/comfort/rationale/confidence fields. Add a pipeline view with explicit stage status and readback/outcome. Add Local AI fallback and learning state without treating Gemini unavailability as total engine failure.

## Vault
Preserve masked display and explicit manual key selection. Never auto-select another account on 429.

## Regression
Preserve current HUD, manual refresh semantics, MIUI/freeform launcher, telemetry, battery UI sync work, and observer-only hardware boundary. Run static checks for direct sysfs/network mutation and stale-value carryover before APK build.
