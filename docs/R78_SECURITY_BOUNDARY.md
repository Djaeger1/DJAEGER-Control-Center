# Control Center r78 security boundary

The Android application is a transparency and user-orchestration surface. Hardware authority stays in DJAEGER's validated local/native control plane.

Forbidden in Control Center application code:
- direct writes to `/sys` or `/proc/sys`
- direct CPU/GPU/thermal node writes
- arbitrary root command execution assembled from UI input
- iptables/nftables mutation
- DNS/route/proxy/game-traffic mutation
- treating Gemini text as an executable shell plan
- reconstructing a missing strategy formula from telemetry

Allowed privileged interaction must be narrow, typed and implemented through the existing DJAEGER module interface. Reads should use coherent snapshots where possible. Key-vault actions are explicit user actions and full API key material must never be rendered back to UI/logs.
