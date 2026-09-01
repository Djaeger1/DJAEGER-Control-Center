# DJAEGER Control Center r9 Consolidation Contract

Status: implementation gate

## Baseline

- Preserve the proven r7 visual layout and Network Intelligence presentation.
- Preserve r8 atomic `cc_snapshot` transport.
- Target DJAEGER control-plane r23 Self Diagnostics Bug Ledger.
- Control Center remains telemetry/orchestration UI; it is not hardware authority.

## Mandatory architecture

### 1. One-second polling path

The recurring 1 Hz UI refresh MUST read only `/data/adb/djaeger_ai/cc_snapshot` through root.

It MUST NOT scan `/sys/class/thermal/thermal_zone*`, CPU cpufreq, KGSL, battery sysfs, network routes, DNS, firewall, proxy, or game traffic during recurring UI polling.

If `cc_snapshot` is absent, the UI fails closed to unavailable/stale values. A compatibility fallback may read bounded DJAEGER-owned state files only; it must not restore whole-device sysfs scanning.

### 2. Snapshot sections

The parser must tolerate missing/unknown sections and consume, when published:

- `__INSTALLED__`
- `__VERSION__`
- `__RUNTIME__`
- `__TEL__`
- `__NETWORK__`
- `__BRAIN__`
- `__ENV__`
- `__HTTP__`
- `__SERVER__`
- `__DECISIONS__`
- `__PLANS__`
- `__FRAME__`
- `__LOG__`
- `__REASONING__`
- `__RESYNC__`
- `__EXECUTION__`
- `__POLICY_CONTEXT__`
- `__ATTRIBUTION__`
- `__BUG_HEALTH__`
- `__BUG_EVENTS__`

Unknown data is rendered as `—`, UNKNOWN, STALE, or unavailable; it is never invented.

### 3. Bug & Health source of truth

Official DJAEGER bug notifications originate only from `__BUG_HEALTH__` and `__BUG_EVENTS__` produced by the local deterministic control-plane detector.

Monitor-side heuristics such as FPS drop or temperature interpretation are informational only and MUST NOT create an official DJAEGER bug notification.

Gemini may provide a cause hypothesis, but the UI must label it `HYPOTHESIS`; it cannot overwrite detector facts or bug state.

### 4. Notification delivery

Control Center owns Android notification delivery.

- Persist the last delivered Event ID in app-local storage.
- Never expose or persist raw Gemini API keys in notification state.
- Do not repeatedly notify the same Event ID on each 1 Hz poll.
- HIGH and CRITICAL events are notification eligible.
- WARNING may notify when `NOTIFY_PENDING=1` or equivalent is published.
- INFO is visible in Bug & Health and is non-intrusive by default.
- A resolved event remains visible as RESOLVED; it is not treated as a new failure.
- Android 13+ notification permission must be handled without blocking telemetry if denied.

### 5. Bug & Health UI

The page/card should expose sanitized fields when available:

- health/open state
- severity
- component
- bug code
- Event ID
- observed facts/symptom
- hypothesis (explicitly labelled)
- automatic action/recovery state
- Decision ID
- Transaction ID
- recent bug ledger events
- Copy Diagnostic Report

Copy Diagnostic Report MUST exclude raw vault files, API keys, credentials, tokens, and unrelated private data.

### 6. Key Vault

Key Vault status is on-demand, not part of 1 Hz polling.

Use only typed `djaeger-ai` key-vault commands. Display index/alias and masked suffix only. Never `cat` the raw vault. Manual key selection is allowed. HTTP 429 quota exhaustion MUST NOT automatically rotate accounts/keys; use Local AI/backoff. Automatic failover is limited to invalid/revoked/permission failure according to control-plane policy.

### 7. Authority and safety

Control Center MUST NOT directly write CPU/GPU/thermal sysfs and MUST NOT modify routes, DNS, firewall, proxy, or game traffic.

Hardware writes remain owned by the Local AI/native typed executor under kernel/native thermal authority with readback verification and restoration semantics.

### 8. Build gate

Do not call the next APK mature until all of these pass:

1. source no longer contains recurring whole-device sysfs telemetry scan;
2. atomic snapshot parser regression tests pass;
3. missing/stale/malformed snapshot tests fail closed;
4. Bug Health parser tests pass;
5. notification Event-ID dedup tests pass;
6. raw-secret regression scan passes;
7. no direct hardware/network mutation regression passes;
8. release build succeeds;
9. APK signing verification and ZIP integrity pass;
10. final matched-stack runtime validation is performed separately on hardware.

Kernel R5 is outside this Control Center consolidation and is not modified by this work.
