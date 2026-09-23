# DJAEGER AI Adaptive — Final Consolidation Audit

Date: 2026-09-23
Branch: `final/djaeger-ai-adaptive-v1`
Baseline consensus: `84f13ea532b7f7bc1b36c528669300e52c44a302`
Runtime quarantine proof head: `d8d7cdfb5590ac2f64f97ab960c3fb2844bd1e05`

## Contract

DJAEGER AI Gaming only. Do not mix DJAEGER Work / Hermes Work.

Decision hierarchy:
1. Gemini primary / highest brain.
2. ONE HERMES deputy identity: Local + Cloud.
3. Cloud/reasoners propose only.
4. Local AI Agent executor is the only hardware/sysfs writer.
5. Native/vendor thermal control remains authoritative and active.

Optimization priority:
1. Frame stability / visual comfort.
2. Thermal comfort.
3. Minimum power.

Hard new-transaction gate:
- skin >= 46 C
- battery >= 45 C
- CPU >= 75 C
- GPU >= 75 C

Skin >= 42 C is soft human-comfort pressure, not a hard execution ban.

## Live-proven runtime

The installed phone runtime has already proven:

- Contextual Shadow hierarchy 1h -> 6h -> 24h.
- Same package + candidate ranges + CPU +/-20% + skin +/-3 C cohort filtering.
- Insufficient contextual cohort => WAITING, never forced PASS.
- Local frame recovery before Cloud.
- Contextual critical recovery stage 1 = BIG+GPU.
- Contextual Shadow V4 range restoration.
- Frame causality gate: historical bad-frame mode was not an underclock condition.
- Unsupported blind boost => local observe, no Cloud.
- Hard thermal hold => no new sysfs transaction.
- Multi-reject / alternate-local-strategy learning.
- Executor/readback/rollback safety.
- ONE HERMES Thought V3.4 live publication.

Latest live game proof included:

```
V3_4_GAME_VERIFY=PASS
HERMES_ACTIVE_SOURCE=HERMES_LOCAL
WORKER_VERSION=ONE_HERMES_THOUGHT_V3_4
ORIGIN=LOCAL_REASONING
PROGRESS=STEADY
FRAME_CLASS=FRAME_SMOOTH
EXECUTOR_STATE=IDLE
ACTIVE_DIGEST=NONE
```

## Source consolidated successfully

Official source now contains:

- `observer-next/module/bin/hermes_thought_worker.sh`
  - ONE HERMES Thought V3.4 promoted from runtime patch.
- `observer-next/module/bin/hermes_adapter.sh`
  - contextual healthy frame reference
  - causality gate
  - local frame recovery before Cloud
  - critical BIG+GPU stage 1
  - healthy local observe before Cloud
  - multi-strategy reject learning / alternate local actuator synthesis
- `observer-next/module/bin/publisher.sh`
  - accepts Hermes Thought only when worker version is V3.4
  - Hermes Thought overrides publisher canned text only while a Hermes source is active
  - persistent Memory display capacity restored to 104857600 bytes (100 MiB)
  - memory capacity explicitly treated as persistent storage, not resident RAM
  - live active CPU/GPU policy bounds are published to Control Center
- `observer-next/module/bin/observer.sh`
  - reads active Little/Big/GPU min/max policy bounds read-only for live UI truth.

Reconstructed, audited but NOT active:
- `final-candidates/shadow.contextual.v4.sh`
  - CONTEXTUAL_SHADOW_V2
  - CONTEXTUAL_SHADOW_V3_PARSEFIX
  - CONTEXTUAL_SHADOW_V4_RANGEFIX
  - SHADOW_CONTEXT_RESET_V1
  - PERSIST_REJECT_STRATEGY_MULTI
  - MULTIACTUATOR_PERSIST_NORMALIZE

Credential migration remains isolated from DJAEGER Work / Hermes Work and preserves the allowlisted Gemini/Hermes credential fields without publishing secrets.

No final-consolidation commit triggered a workflow/build.

## Build blockers — DO NOT BUILD FINAL PAIR YET

### 1. Active shadow source is not consolidated

The repository write interface rejected updates to:
`observer-next/module/bin/shadow.sh`

The reconstructed final source is preserved at:
`final-candidates/shadow.contextual.v4.sh`

The final module must not be built until the audited candidate can replace the active shadow path and pass syntax/contract tests.

### 2. Thought worker startup lifecycle is not consolidated

The repository write interface rejected updates to:
`observer-next/module/service.sh`

Current live phone runtime is fine because the runtime installer launched Thought V3.4, but a fresh module built from current source would not yet automatically start `hermes_thought_worker.sh`.

This is a final-build blocker.

### 3. Three literal temporary-path defects remain in final source

Read-only audit found fixed-name `.tmp.$` paths instead of process-unique `.tmp.$$`:

- two in `observer-next/module/bin/hermes_adapter.sh`
- one in `observer-next/module/bin/hermes_thought_worker.sh`

Runtime proof shows these were not fatal on the installed phone, but they must be corrected before declaring source final.

Write attempts to correct them were rejected by the repository tool.

### 4. Reject-quarantine barrier ordering needs correction

Current consolidated Hermes source has the first Cloud fallback before
`REJECT_QUARANTINE_OBSERVE_BARRIER`.

The barrier contract says a locally rejected/quarantined strategy must not fall through to Cloud in the same decision cycle. Therefore the barrier should precede the first Cloud fallback.

The attempted ordering correction was rejected by the repository write tool.

This is a neuron-efficiency/source-correctness blocker, even though the already-proven live runtime remains safe.

## UI audit

- Memory UI reads module-published `USED_BYTES/MAX_BYTES`, so the 100 MiB source contract is wired to the existing UI.
- Current telemetry clocks are available.
- Active policy min/max bounds are now read by the module and published as live execution ranges.
- Existing Control Center labels `EXEC_GPU` as MHz while the module field remains kernel-Hz semantics. APK/unit alignment still needs a final source edit before release.
- No redesign of the existing Overview layout is required.

## Memory audit

Current bounded storage mechanisms already include:
- telemetry compaction around the existing 3 MiB telemetry file threshold
- Thought knowledge compaction above 8 MiB to recent learned mappings
- multi-reject ledger bounded to recent rows

The 100 MiB figure is a persistent knowledge/storage capacity, not RAM allocation.
A single global hard-cap enforcement layer is not yet present; final release should preserve important outcomes and prune lower-value history rather than blindly deleting learning.

## Release gate

Final module/APK packaging is allowed only after all of these are true:

- active `shadow.sh` equals the audited contextual V4 candidate
- `service.sh` starts/stops/proves `hermes_thought_worker`
- all literal `.tmp.$` defects are corrected to process-unique paths
- reject-quarantine barrier is before Cloud fallback
- GPU live-range unit contract matches the APK
- shell syntax/tests pass
- Android tests/build pass
- no DJAEGER Work/Hermes Work contamination
- no workflow/build is used as a substitute for real-phone validation

Until then, the installed live runtime remains the strongest proven state and must not be replaced by an incomplete build.
