# DJAEGER AI Railway Core v1

Purpose: cloud observability and debugging for DJAEGER AI only.

Safety contract:
- OBSERVE/DEBUG only.
- No sysfs writes.
- No CPU/GPU/thermal/profile authority.
- Local DJAEGER Agent remains execution authority.
- Railway outage must not affect local DJAEGER behavior.

Endpoints:
- GET /health
- POST /v1/device/telemetry
- POST /v1/device/event
- GET /v1/device/state
- GET /v1/debug/traces
- GET /v1/config

Deployment note: LIVEAUDIT rollback-gate repair validated through the DJAEGER AI shadow regression gate.
