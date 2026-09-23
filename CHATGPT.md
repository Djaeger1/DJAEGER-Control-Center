# CHATGPT.md — DJAEGER AI Gaming handover

Updated: 2026-09-23
Project: DJAEGER AI Gaming / DJAEGER Gaming
Repository: Djaeger1/DJAEGER-Control-Center
Final consolidation branch: final/djaeger-ai-adaptive-v1
Current branch head: 8dfd170ea38b9ba7669ac416b9c578c78f46b32c

## Project separation
- This file is for DJAEGER AI Gaming only.
- Never mix code, paths, state, or architecture with DJAEGER Work / Hermes Work.

## Core architecture contract
- Observe real device behavior first: CPU Little/Big, GPU, temperatures, power, FPS/frame-time/jank, workload.
- Gemini = PRIMARY/HIGHEST reasoning brain while online and context-valid.
- ONE HERMES = one deputy identity spanning Local + Cloud.
- Reasoners propose; deterministic local AI Agent/executor is the only hardware/sysfs writer.
- Native Android/vendor thermal/power mechanisms remain active.
- No fixed legacy profiles as the core control strategy.
- Human-comfort objective order:
  1. frame stability / visual comfort,
  2. thermal comfort,
  3. minimum power.
- Soft skin comfort pressure: 42C.
- Hard no-new-transaction gate: skin >=46C OR battery >=45C OR CPU >=75C OR GPU >=75C.
- Persistent Memory capacity: 100 MiB storage, not resident RAM.
- Control Center should show live active CPU/GPU bounds.

## Proven live runtime state
### Adaptive / causal runtime
Proven on real phone:
- contextual shadow hierarchy 1h -> 6h -> 24h,
- local frame recovery before Cloud,
- critical recovery stage1 BIG+GPU,
- causal guard preventing blind boost,
- executor safety / rollback / exact readback behavior,
- hard thermal hold,
- neuron guard.

Key proven runtime commits/patch lineage:
- 0d490b6e751d8ca0f365cd74cf7031147a87b13e — local frame recovery before Cloud
- 93619d841f3372eb3d46adba88e39dbde6a44e37 — critical recovery stage1 BIG+GPU
- 05981319d31be2baace6cac622154a1f34da78e5 — contextual shadow V4 range fix
- 94fd425384c062379a9a5e6fb9f66d5cda8db595 — contextual frame causality V1

Important empirical finding:
- bad-frame mode was not caused by low clock; bad mode already showed higher GPU load/clock and higher power/temperature while CPU was similar.
- Therefore blind CPU/GPU boost is not allowed without causal support.

### ONE HERMES THOUGHT
Live-tested V3.4:
- WORKER_VERSION=ONE_HERMES_THOUGHT_V3_4
- worker PID matched lock PID,
- HERMES_LOCAL game takeover produced a real published V3.4 thought,
- PROGRESS and FRAME_CLASS were present,
- V3_4_GAME_VERIFY=PASS.
- THOUGHT progress is local-evidence driven and does not call Cloud merely to vary UI text.
- Cloud teacher is only for genuinely novel semantic reasoning.
- known local reason classes cost zero thought-neurons.
- Cloud unavailable/limited => Local + learned memory continue.

Observed live proof:
- HERMES_ACTIVE_SOURCE=HERMES_LOCAL
- ORIGIN=LOCAL_REASONING
- PROGRESS=STEADY
- FRAME_CLASS=FRAME_SMOOTH
- executor remained IDLE / ACTIVE_DIGEST=NONE.

## THOUGHT display contract
- THOUGHT must be concise interpretation + decision, not a replay of Overview telemetry.
- Do not repeat FPS, frame-time, jank, temperatures, power, or clocks unless one specific value is essential to explain a decision/change.
- Publisher is display-only; it must not author generic canned reasoning.
- ONE HERMES reasoning is owned by hermes_thought_worker.
- Gemini reasoning should come from the same Gemini primary inference, not a second call.

## Screenshot issue found 2026-09-23
User screenshots showed old publisher templates still repeating:
- FPS,
- jank,
- P95/P99,
- temperatures,
- power,
- clocks.
This violated the THOUGHT contract.

Source-final fixes made:
- Gemini primary inference now requests a 10th line:
  THOUGHT=<short natural Indonesian interpretation/decision without Overview telemetry repetition>
- no second Gemini call is used for THOUGHT.
- Gemini THOUGHT persists in gemini_reasoner.env for both OBSERVE and CANDIDATE.
- Gemini valid OBSERVE confidence also persists in runtime state so UI does not show 0% merely because no proposal file exists.
- publisher reads fresh same-package Gemini THOUGHT; fallback wording is concise and telemetry-free.
- Hermes fallback wording was also shortened and telemetry duplication removed.
- THOUGHT priority corrected to:
  brain reasoning -> Hermes thought override -> shadow event -> executor apply/rollback event.

Relevant final branch commits:
- 9a4c8e03218267c9fdb6a5ddd9cccf23faf938ac — parse Gemini THOUGHT
- 63865c0aea58729ebee3adad1c65f7b1ac259470 — preserve Gemini OBSERVE confidence
- a2dc8d2dc51a46cfff74704cab952403dfb7cecb — concise Gemini/Hermes THOUGHT publisher
- 2677f4ebeacb5167ae7181bc8b4a3f0c274a0d03 — preserve shadow/executor event priority
- 8dfd170ea38b9ba7669ac416b9c578c78f46b32c — publisher uses Gemini OBSERVE confidence

## Source-final consolidation already written
On final/djaeger-ai-adaptive-v1:
- observer-next/module/bin/hermes_adapter.sh
  - local-first frame recovery
  - contextual healthy-frame reference
  - causal frame gate
  - multi-reject alternative synthesis
  - multi-actuator reject normalization
  - hard thermal behavior
- observer-next/module/bin/hermes_thought_worker.sh
  - ONE_HERMES_THOUGHT_V3_4
- observer-next/module/bin/publisher.sh
  - V3.4 Hermes thought display
  - concise Gemini thought path
  - Memory 100 MiB persistent storage contract
  - live active CPU/GPU bounds source
- observer-next/module/bin/gemini_reasoner.sh
  - primary Gemini THOUGHT + confidence state
- observer-next/module/bin/observer.sh
  - live Little/Big/GPU active min/max bounds
- observer-next/android/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt
  - live range formatter converts kHz/Hz to MHz correctly
  - objective text is FRAME STABILITY FIRST / THERMAL COMFORT SECOND / MINIMUM POWER THIRD.

## Live CPU/GPU range contract
observer publishes:
- LITTLE_ACTIVE_MIN_KHZ
- LITTLE_ACTIVE_MAX_KHZ
- BIG_ACTIVE_MIN_KHZ
- BIG_ACTIVE_MAX_KHZ
- GPU_ACTIVE_MIN_HZ
- GPU_ACTIVE_MAX_HZ

publisher exposes them as EXEC_LITTLE / EXEC_BIG / EXEC_GPU with:
- EXEC_RANGE_SOURCE=LIVE_POLICY_BOUNDS

Control Center formats:
- CPU kHz -> MHz
- GPU Hz -> MHz

## Memory contract
publisher final:
- MAX_BYTES=104857600
- CAPACITY_KIND=PERSISTENT_STORAGE_NOT_RAM
- usage is derived from persistent history files.
Telemetry already trims history; thought knowledge compacts when needed.

## Credential migration contract
migrate.sh:
- restores up to four Gemini keys,
- restores Hermes access key/endpoint/cloud id,
- preserves cooldown state when available,
- uses explicit allowlist,
- explicitly rejects DJAEGER Work / Hermes Work paths to prevent project contamination.
Never put raw secrets in CHATGPT.md.

## Final-source blocker resolution
The previous source-consolidation blockers are now resolved in the final branch:

1. Contextual Shadow V4
   - official runtime worker exists at:
     observer-next/module/bin/shadow_contextual_v4.sh
   - contains CONTEXTUAL_SHADOW_V2, V3 parse fix, V4 range fix, context reset, multi-reject persistence, and multi-actuator normalization.
   - consensus.sh consumes runtime/shadow_contextual_v4.env.
   - executor.sh requires DJAEGER_CONTEXTUAL_SHADOW_V4 and approved_contextual_v4.env before execution.

2. Worker lifecycle
   - publisher_worker.sh supervises both:
     - hermes_thought_worker.sh
     - shadow_contextual_v4.sh
   - this provides a legitimate runtime lifecycle without requiring an extra privileged service.sh startup hook.

3. Reject/quarantine Cloud barrier
   - cloud_takeover() itself rejects both:
     - shadow_rejected_strategy_quarantine
     - all_local_comfort_strategies_quarantined
   - HCLOUD_USED=NO and no Cloud request is made for these known rejected local strategies.
   - therefore neuron safety does not depend on the later display/observe barrier ordering.

## Build policy
- Do not flash/reboot merely to test source consolidation.
- Runtime patch evidence remains authoritative for behavior already proven on the real phone.
- Source consolidation blockers are resolved.
- Before final synchronized module + APK build, perform one combined structural audit and hot-validate the new concise Gemini/ONE HERMES THOUGHT path during a real game.

## Current next action
Continue from branch:
final/djaeger-ai-adaptive-v1

Priority:
1. final structural audit of brain -> shadow -> executor -> publisher contracts,
2. hot-patch the currently installed reasoner/publisher only,
3. verify concise THOUGHT live for Gemini and ONE HERMES with no Overview telemetry repetition,
4. verify neuron accounting and executor safety remain unchanged,
5. then build the final synchronized module + APK pair.
