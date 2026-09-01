# DJAEGER Control Center — r78 Runtime Contract

Control Center remains an observer/orchestrator. It MUST NOT write sysfs, thermal nodes, CPU/GPU nodes, routes, DNS, firewall, proxy, or game traffic.

## Runtime root

Canonical runtime root: `/data/adb/djaeger_ai`.

## Core state

Read `runtime_status` for controller_pid, predictor_pid, active, game, window_mode, user_mode, updated_at.
Read `root_authority_state` for authority lifecycle including RESTORED.
Read `cc_snapshot` for UI telemetry and brain state.

## Strategy Composition

The UI MUST display only fields actually published by `gemini_strategy_formula.env`. It MUST NOT reconstruct or guess a Gemini formula.

Expected composition fields include CPU_LITTLE_MIN/MAX, CPU_BIG_MIN/MAX, GPU_MIN/MAX, CPU_GOVERNOR, GPU_GOVERNOR, owner mode/profile, game/context, capability generation/signature/epoch, observation identity/timestamp/FPS provenance, rationale/confidence when published, and other typed bounded strategy fields published by the module.

If the formula file is absent or incomplete, render `No validated Gemini formula` and preserve Local AI/fallback state separately.

## Strategy Result

Read `gemini_strategy_result.env` as the sole source for the execution pipeline. Render stages from published state only:

`PROPOSED → VALIDATED/REJECTED → APPLIED → READBACK VERIFIED → OUTCOME`

Never infer APPLIED or VERIFIED from a proposal. OUTCOME may remain PENDING until a transaction-bound mature observation exists.

## Local AI and fallback

Expose source/mode from `cc_snapshot` brain state, including LOCAL_BASELINE/OFFLINE_BASELINE and learned strategy states. A Gemini HTTP failure must not be displayed as an engine failure when Local AI is actively controlling safely.

## Gemini state

Read `gemini_http_state`, `gemini_resync_state`, and `gemini_server_state` independently. HTTP 200 from a secondary/server interaction is not proof that the primary reasoning/formula pipeline succeeded. HTTP 429 is quota/backoff state and must not trigger automatic account/key rotation.

## Key Vault UX

Keys are always masked. Allow manual active-key selection/removal/addition through the existing privileged module interface only; Control Center never exposes full key material. Do not auto-rotate on HTTP 429. Automatic failover is permitted only for invalid/revoked/permission failure when supported by the module policy.

## Telemetry

Use `cc_snapshot` as the primary coherent snapshot. Show ACTIVE/IDLE, game, window mode, CPU/GPU/skin/battery, FPS/frame-time provenance, network read-only metrics, profile, Local AI source and learning state. Never label FPS as live-verified unless the module publishes verified producer provenance.

## Freshness and fail-closed UI

Every section must show stale/unavailable rather than reusing an old value as current. Historical adaptive envelopes may remain on disk while runtime is IDLE; they are memory, not active execution. `root_authority_state=RESTORED` and runtime active=0 take precedence for execution-state presentation.

## r78 validated device behavior

The matched-device runtime validation established the intended UI states for boot/idle, Arcane Legends ACTIVE, MULTIWINDOW, Local AI fallback on Gemini quota, teardown, and Root Authority RESTORED. Control Center must preserve these distinctions instead of collapsing them into a single online/offline badge.
