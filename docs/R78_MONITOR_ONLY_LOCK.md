# DJAEGER Control Center r78 — MONITOR ONLY LOCK

This decision supersedes orchestration/control plans for the next Control Center build.

Control Center is a pure monitoring and transparency application.

## Allowed
- read coherent DJAEGER runtime snapshots
- display ACTIVE/IDLE, game, session/window mode
- display CPU/GPU/skin/battery/FPS/frame-time telemetry with provenance/freshness
- display network intelligence strictly read-only
- display Local AI/Gemini source and fallback/backoff state
- display Gemini Strategy Composition exactly as published by the module
- display validation/apply/readback/outcome pipeline exactly as published by the module
- display learning samples/confidence/promotion state
- display Root Authority state
- manual UI refresh of monitoring data only

## Forbidden
- no sysfs/proc writes
- no CPU/GPU/governor/thermal/power changes
- no mode switching
- no reset/apply/boost buttons
- no Key Vault add/select/remove actions
- no API-key writes or rotation controls
- no Gemini request trigger
- no root command assembled from UI input
- no route/DNS/firewall/proxy/network/game-traffic mutation
- no starting/stopping/restarting DJAEGER services
- no editing DJAEGER runtime/config files

## Key monitoring
The UI may show only module-published masked active-key/account status and Gemini HTTP/quota/auth state. It cannot change the active key.

## Strategy monitoring
The app never reconstructs a formula. Missing/stale formula/result files render unavailable/stale. Proposal is visually distinct from actual applied/readback/outcome state.

## Authority
DJAEGER module + Local AI/native control plane remain the sole hardware/control authority. Control Center cannot alter decisions.
