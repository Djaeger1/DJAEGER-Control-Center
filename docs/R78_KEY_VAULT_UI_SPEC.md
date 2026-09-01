# r78 Key Vault UI specification

Purpose: make multiple configured Gemini credentials manageable without exposing secrets or turning quota handling into automatic account rotation.

Display only:
- slot/key label
- masked fingerprint/suffix supplied by the module
- active/inactive state
- availability/auth state when published
- last selected/used metadata when safely published

Explicit actions:
- add key through the module's typed vault interface
- manually select active key
- remove a selected stored key with confirmation

Rules:
- never read/render/log the full key after storage
- never copy a full key into telemetry, crash reports or reasoning logs
- HTTP 429 does not select another key automatically
- invalid/revoked/permission failure may use module-governed failover if the module policy explicitly supports it
- manual selection is a user action and should be clearly reflected in the UI
