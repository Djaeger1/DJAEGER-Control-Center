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

## Known blockers before final module+APK build
Do NOT claim final pair complete yet.

1. Active source path observer-next/module/bin/shadow.sh
   - direct connector writes to this path were blocked by tool safety.
   - reconstructed final candidate exists at:
     final-candidates/shadow.contextual.v4.sh
   - candidate includes contextual V2, V3 parse fix, V4 range fix, context reset, multi-reject persistence, and multi-actuator normalization.
   - active source path still needs legitimate promotion before final build.

2. observer-next/module/service.sh
   - connector write to add hermes_thought_worker lifecycle/startup was blocked by tool safety.
   - final build must not proceed until startup lifecycle is represented legitimately.
   - runtime V3.4 worker was manually installed/restarted and is live-tested, but source startup integration is not yet committed.

3. Hermes reject barrier ordering
   - audit found REJECT_QUARANTINE_OBSERVE_BARRIER is still after the first Cloud fallback in source-final hermes_adapter.
   - intended order is:
     HARD THERMAL -> LOCAL FRAME -> CAUSAL BARRIER -> REJECT/QUARANTINE BARRIER -> CLOUD.
   - connector write attempting to move this barrier was blocked.
   - do not mark neuron-flow source final until this is resolved.

## Build policy
- Do not build/install the final module+APK while the three blockers above remain.
- Do not flash/reboot merely to test source consolidation.
- Runtime patch evidence is authoritative for already proven behavior.
- Final pair comes only after a final combined source audit and all blocked source paths are legitimately resolved.

## Current next action
Continue final source consolidation from branch:
final/djaeger-ai-adaptive-v1
head:
8dfd170ea38b9ba7669ac416b9c578c78f46b32c

Priority:
1. resolve shadow active-source promotion,
2. resolve service startup lifecycle for hermes_thought_worker,
3. move reject/quarantine barrier before first Cloud fallback,
4. run structural/syntax audit,
5. hot-validate concise THOUGHT during real game,
6. only then build final synchronized module + APK pair.
