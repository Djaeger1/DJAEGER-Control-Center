# CHATGPT.md — DJAEGER GAMING Project Memory

> **Purpose:** This file is the persistent handover / single source of truth for ChatGPT sessions working on **DJAEGER GAMING**.
> Read this file before making changes. Update it whenever a chat produces an important final decision, architecture change, verified state, active blocker, or next action.
> Do **not** store raw API keys, tokens, passwords, private signing keys, or other secrets here.

## 1. PROJECT IDENTITY

Project: **DJAEGER GAMING**

Primary goal:
- Build an adaptive Android gaming engine that observes real device behavior and lets the local/cloud agents derive and apply the best operating decisions from telemetry rather than relying only on rigid static presets.

Project isolation:
- **DJAEGER GAMING is NOT DJAEGER Work / Hermes Work.**
- Never import DJAEGER Work video automation, worker logic, runtime state, contracts, or files into DJAEGER GAMING unless explicitly requested.
- Other DJAEGER projects must keep their own project memory.

Repository currently hosting this handover:
- `Djaeger1/DJAEGER-Control-Center`


## PROJECT NAME / ALIAS RULE

- **Canonical current name:** `DJAEGER GAMING`
- **Accepted current aliases:** `DJAEGER GAMING`, `DJAEGER AI GAMING`
- These two names refer to the same current project.
- **Plain `DJAEGER AI` alone is NOT the preferred current-project name** because it may refer to the older DJAEGER AI lineage.
- If the user says `DJAEGER GAMING` or `DJAEGER AI GAMING`, load this current project memory.
- If the user says only `DJAEGER AI`, first treat it as legacy/ambiguous unless the surrounding context clearly identifies the current gaming project.
- The user may forget which of the two current aliases they used previously; do not force them to remember the exact wording.


## 2. ABSOLUTE OPERATING RULES

1. **Real-device evidence beats self-test.**
   - Server PASS, mock PASS, unit test PASS, or local simulation does not prove the installed phone runtime works.
   - A feature is only "live verified" when evidence from the actual installed device proves it.

2. **Do not repeat completed work.**
   - Check the latest verified state before rebuilding or re-patching a component that already passed.

3. **Do not ask for disruptive device actions casually.**
   - Avoid flash, reboot, reinstall, or manual terminal work unless there is no safe remote path and the reason is explicit.
   - Audit first, then act.

4. **Protect the stable baseline.**
   - Do not use the known-stable baseline as an experimentation area.
   - Experimental changes must have a clear rollback path.

5. **Keep Control Center truthful.**
   - UI status such as Cloud READY/OFFLINE, Cloud in control, Cloud plan, source/reasoner, neuron usage, and runtime state must reflect the real source of truth.
   - Never infer success from a UI label alone.

6. **Keep secrets out of this file.**
   - Credentials may be referenced only as "configured externally" or by non-secret identifier.
   - Never commit raw API keys, auth tokens, passwords, or private keys.

## 3. DESIGN DIRECTION

Current design direction agreed in chat:
- Prefer **adaptive observation + analysis** over forcing the phone into a large set of hand-made static profiles.
- Observe real processor and device behavior, including where available:
  - CPU state / frequencies
  - GPU state / frequencies
  - frame behavior / frame pacing / jank
  - thermal sensors
  - power / battery behavior
  - memory pressure
  - network / latency signals
  - workload context
- Let the agent stack (local agent / Hermes / Gemini or other configured reasoners) analyze this telemetry and derive the operating decision/preset.
- The engine should keep only the components genuinely required for this closed loop.
- The existing **Overview** layout is considered comfortable and should not be redesigned casually.

Conceptual loop:

```text
OBSERVE REAL DEVICE
      ↓
ANALYZE
      ↓
FORMULATE DECISION / PRESET
      ↓
APPLY SAFELY
      ↓
MEASURE OUTCOME
      ↓
LEARN / CORRECT
      ↓
REPEAT
```

## 4. CURRENT CANONICAL ARTIFACT PAIR — DJAEGER GAMING v1.1.8 V3.4 FINAL

This is the **current canonical built artifact pair** as of 2026-09-23. It was installed on the real phone. Post-install validation discovered one packaging/lifecycle gap in the module: V3.4 `hermes_thought_worker.sh` was not included in `service.sh` startup lifecycle, and its knowledge TSV was not initialized on a clean first boot. The current phone is now **live verified with POSTINSTALL_HOTFIX1**; the original ZIP itself must not be described as defect-free.

Canonical pair:
- APK: `DJAEGER-GAMING-v1.1.8-V3.4-FINAL.apk`
- APK version: `1.1.8-v3.4-final`
- APK versionCode: `112`
- APK SHA-256: `97bc32bb68c93fa8ac6527a86bd18bd0a1b4752b13b0a65192f6fc3be03cca37`
- Module: `DJAEGER-GAMING-Module-v1.1.8-V3.4-FINAL.zip`
- Module versionCode: `211`
- Module SHA-256: `7c7fcd05682b7543f9668c7b58c698973cba8a47b5f9127fa677bf92b683a5d8`
- Build branch: `djaeger-gaming-v3.4-final-consolidation`
- Build source commit: `fb2c41009e20416deff88523c84fe02072b33fb4`
- GitHub Actions final-pair run: `35873269162`
- Artifact ID: `10757025416`
- Artifact archive digest: `sha256:4464b8d2ada6d9d35b8be6f70a3f27d2b46a6967bfcd2267db8423abb5d05635`

Verified build properties:
- Source isolation: PASS
- Shell syntax: PASS
- V3.4 lifecycle / Shadow / memory gates: PASS
- Module contract + fake-sysfs regressions: PASS
- Android unit tests + release build: PASS
- APK package identity: `com.djaeger.observer` / VC112 / `1.1.8-v3.4-final`
- Launcher label: `DJAEGER GAMING`
- APK Signature Scheme v2: PASS
- APK Signature Scheme v3: PASS
- Signer certificate SHA-256: `bb3f854a7763b5f9a5c87d279e3cbf1c538b03d9ab120f6b375a97c8d06b0269`
- Thought worker: `ONE_HERMES_THOUGHT_V3_4`
- Persistent memory ceiling: `104857600` bytes (100 MiB)
- Published execution range source: `LIVE_POLICY_BOUNDS`
- Cloud hardware authority: NONE
- Sysfs authority: AI Agent internal executor only

### Known post-install issue / HOTFIX1

Real-device evidence after installing module VC211 + APK VC112 found:
- APK identity on device: `versionCode=112`, `versionName=1.1.8-v3.4-final`.
- Module identity on device: `versionCode=211`, `version=1.1.8-v3.4-final`.
- Pair handshake: `PAIR_VERIFIED=YES`.
- `service.sh` from the original final ZIP did **not** start `hermes_thought_worker.sh` after reboot.
- `hermes_thought_worker.err` showed repeated missing-file errors for `history/hermes_thought_knowledge.tsv`.

Live-device HOTFIX1 applied without flash/reboot:
- patched installed `service.sh` so `hermes_thought_worker` participates in stop/kill/start/startup-proof lifecycle;
- initialized persistent `history/hermes_thought_knowledge.tsv` with the expected header and mode 600;
- restored the worker binary to the original artifact copy after an unsuccessful experimental inline edit, then started the original V3.4 worker cleanly;
- V3.4 worker owner PID became singleton and healthy; timestamp advanced, `LAST_STAGE=PUBLISHED`, `LAST_ERROR=NONE`, and error log stopped growing.

Source HOTFIX1:
- Branch: `djaeger-gaming-v3.4-postinstall-hotfix1`
- Service lifecycle fix commit: `ff7123ad7318fca34f6ef8ca2b413e33ea2332f5`
- Worker first-boot knowledge init commit: `3c6e816e1639766bf082d940f2f73ac24245c800`
- Audit head: `3165fe4bff0211cf933a54f54fa52df22af88829`
- Audit run: `35876436725` — SUCCESS
- Audit gates: source isolation PASS, shell syntax PASS, hotfix contract/module regressions PASS, Android unit tests PASS.

Signing caveat:
- This final APK uses a **new release signer** because no persistent prior private signing key was available.
- Therefore drop-in Android update over an older installed APK is **not guaranteed**.
- Do not confuse signer compatibility with module/runtime compatibility; module state/credential recovery is separate.

Hard rule:
- **BUILD SUCCESS ≠ DEVICE SUCCESS**
- **ARTIFACT VALID ≠ INSTALLED RUNTIME VALID**
- Do not promote this pair to `VERIFIED_LIVE` until post-install real-device evidence passes.

Historical note:
- v1.1.7 adaptivefix (module 210 / app 111) is superseded historical evidence and is **not** the currently installed pair. The current phone is proven on module 211 / app 112 with POSTINSTALL_HOTFIX1.

## 5. ADAPTIVE ENGINE CONTRACT

The long-term target is not simply "pick a fixed profile".
The system should:
- observe real workload behavior,
- reason about performance vs heat vs power,
- choose the smallest safe intervention,
- avoid unnecessary boosting,
- prefer stability and battery efficiency outside heavy workloads,
- validate the result,
- learn from outcomes,
- and be able to revert when a decision worsens the device state.

Static named profiles may still exist as bounded execution targets / safety envelopes, but they must not replace real telemetry-based reasoning.

## 6. UI / THOUGHT PANEL CONTRACT

- The Overview layout should remain recognizable unless the user explicitly asks for redesign.
- The THOUGHT panel should be concise.
- Do not repeat telemetry already visible in Overview.
- THOUGHT should focus on:
  - interpretation,
  - decision,
  - reason for change,
  - next expected effect.
- Numeric telemetry should be repeated only when it materially explains a decision.

## 7. MEMORY / LEARNING CONTRACT

- Agent persistent memory is storage for useful knowledge/outcomes, not a reason to keep everything resident in RAM.
- Use lightweight indexed storage, lazy loading, pruning, and compaction.
- Low-value history should be discarded rather than allowing the knowledge store to become noise.

## 8. VERIFICATION STANDARD

Before declaring a DJAEGER GAMING change complete, prefer evidence in this order:

1. Real device runtime evidence.
2. Real device telemetry reaching the intended component.
3. Correct action/decision observed on device.
4. Backend / bridge logs that correlate with the device event.
5. Build / unit / self-test evidence.

Items 4–5 support the conclusion but do not replace items 1–3 when the feature depends on the actual phone.

## 9. CHATGPT HANDOVER WORKFLOW

At the end of any important DJAEGER GAMING session:

1. Update **CURRENT VERIFIED STATE**.
2. Add newly finalized decisions.
3. Remove or clearly mark superseded decisions.
4. Record unresolved blockers.
5. Record the exact next action.
6. Do not paste huge raw logs; summarize the evidence and keep pointers (commit, file, endpoint, version) where useful.
7. Never claim a state is verified if it was only inferred.

At the start of a new session:
1. Read this file first.
2. Inspect current source / commit / runtime evidence.
3. Reconcile any newer evidence with this file.
4. Continue from the unresolved next action instead of restarting from zero.

## 10. CURRENT VERIFIED STATE

This section must only contain facts verified from current project/repository/device evidence.

```text
PROJECT=DJAEGER GAMING
MEMORY_FILE=CHATGPT.md
MEMORY_REPOSITORY=Djaeger1/DJAEGER-Control-Center
MEMORY_BRANCH=main

LATEST_CANONICAL_ARTIFACT_PAIR=v1.1.8-v3.4-final
LATEST_CANONICAL_APK=DJAEGER-GAMING-v1.1.8-V3.4-FINAL.apk
LATEST_CANONICAL_APK_VERSION_CODE=112
LATEST_CANONICAL_APK_SHA256=97bc32bb68c93fa8ac6527a86bd18bd0a1b4752b13b0a65192f6fc3be03cca37
LATEST_CANONICAL_APK_SIGNER_SHA256=bb3f854a7763b5f9a5c87d279e3cbf1c538b03d9ab120f6b375a97c8d06b0269
LATEST_CANONICAL_MODULE=DJAEGER-GAMING-Module-v1.1.8-V3.4-FINAL.zip
LATEST_CANONICAL_MODULE_VERSION_CODE=211
LATEST_CANONICAL_MODULE_SHA256=7c7fcd05682b7543f9668c7b58c698973cba8a47b5f9127fa677bf92b683a5d8
LATEST_CANONICAL_BUILD_BRANCH=djaeger-gaming-v3.4-final-consolidation
LATEST_CANONICAL_BUILD_COMMIT=fb2c41009e20416deff88523c84fe02072b33fb4
LATEST_CANONICAL_BUILD_RUN=35873269162
LATEST_CANONICAL_ARTIFACT_ID=10757025416
CANONICAL_ARTIFACT_STATUS=BUILD_VERIFIED_KNOWN_POSTINSTALL_LIFECYCLE_GAP

LATEST_DEVICE_VERIFIED_PAIR=v1.1.8-v3.4-final+POSTINSTALL_HOTFIX1
LATEST_DEVICE_VERIFIED_AT=2026-09-23T21:46:25+07:00
LATEST_DEVICE_APK_VERSION_CODE=112
LATEST_DEVICE_MODULE_VERSION_CODE=211
LATEST_DEVICE_PAIR_VERIFIED=YES
LATEST_DEVICE_RUNTIME_STATUS=LIVE_VERIFIED_WITH_POSTINSTALL_HOTFIX1
LATEST_DEVICE_RUNTIME_EVIDENCE_AT=2026-09-23
LATEST_DEVICE_HERMES_ACTIVE_SOURCE=HERMES_LOCAL
LATEST_DEVICE_THOUGHT_WORKER_VERSION=ONE_HERMES_THOUGHT_V3_4
LATEST_DEVICE_THOUGHT_LAST_STAGE=PUBLISHED
LATEST_DEVICE_THOUGHT_LAST_ERROR=NONE
LATEST_DEVICE_MEMORY_MAX_BYTES=104857600
LATEST_DEVICE_EXEC_RANGE_SOURCE=LIVE_POLICY_BOUNDS
LATEST_DEVICE_SHADOW_STATE=REJECT
LATEST_DEVICE_SHADOW_REASON=human_comfort_contract_failed_POWER_EFFICIENCY
LATEST_DEVICE_CONTROL_GATE=SAFE_REJECT_VERIFIED
LATEST_DEVICE_EXECUTOR_STATE=IDLE
LATEST_DEVICE_TELEMETRY_HTTP=200
LATEST_DEVICE_TELEMETRY_MODULE_VERSION_CODE=211
LATEST_DEVICE_GEMINI_KEY_COUNT=4
LATEST_DEVICE_HERMES_ACCESS_KEY_PRESENT=YES
LATEST_DEVICE_NEURON_LOCAL_ESTIMATE_PRESENT=YES
LATEST_DEVICE_HOTFIX=POSTINSTALL_HOTFIX1
LATEST_DEVICE_REBOOT_PERSISTENCE=SOURCE_AUDITED_NOT_SECOND_REBOOT_TESTED
```

Interpretation:
- Real-device package identity is now proven: module VC211 + APK VC112, version `1.1.8-v3.4-final`, handshake `PAIR_VERIFIED=YES`.
- The current phone is **LIVE_VERIFIED_WITH_POSTINSTALL_HOTFIX1**, not the untouched original ZIP state.
- V3.4 THOUGHT is live with one singleton owner, `HERMES_LOCAL`, `LAST_STAGE=PUBLISHED`, `LAST_ERROR=NONE`, and advancing timestamps.
- Memory ceiling is 100 MiB and publisher reports `EXEC_RANGE_SOURCE=LIVE_POLICY_BOUNDS`.
- Railway receives fresh VC211 telemetry with HTTP 200 during real workloads, including the game package `sts.al`.
- Nonsecret credential continuity is proven by `GEMINI_KEY_COUNT=4`, `HERMES_ACCESS_KEY_PRESENT=YES`, and local neuron estimate present.
- A second reboot has **not** been performed solely to re-prove persistence; the installed `service.sh` is patched and source HOTFIX1 audit passed, so do not ask for another reboot casually.

## 11. ACTIVE BLOCKERS

- Current device runtime is healthy after `POSTINSTALL_HOTFIX1`; no reinstall or reboot is required now.
- The original v1.1.8 module ZIP has a known first-boot lifecycle gap and must not be reused as a clean-install "perfect final" without HOTFIX1.
- Source HOTFIX1 is audited successfully but has **not** been repackaged into a new release identity. Do not silently rebuild different bytes under the same v1.1.8 / VC211 identity.
- A future packaged cleanup release must use a new version/versionCode and include both lifecycle + knowledge-init source fixes.
- Post-install adaptive safety path is verified: a real candidate reached Shadow and was rejected with `human_comfort_contract_failed_POWER_EFFICIENCY`; executor correctly remained IDLE. A successful APPLY/readback cycle has not yet been re-exercised after this install and should not be forced artificially.
- APK signer continuity caveat remains historical for older APKs, but APK VC112 is now installed successfully on the current phone.

## 12. NEXT ACTION

On the next DJAEGER GAMING work session:
- Read this file before answering version/state questions.
- Start from **v1.1.8 V3.4 FINAL + POSTINSTALL_HOTFIX1 live on device**; do not reinstall the original v1.1.8 pair and do not repeat the completed post-install checks.
- Use source branch `djaeger-gaming-v3.4-postinstall-hotfix1` as the latest fixed source reference.
- The documented safe-reject path is already verified. Continue normal gameplay; if a naturally safe candidate later reaches APPLY, verify readback and KEEP/ROLLBACK without forcing hardware intervention.
- Preserve the rule: no cloud sysfs authority; only the local AI Agent executor may write hardware bounds.
- Do not make a new packaged release unless needed. If packaging is later required, bump version/versionCode and include HOTFIX1; never publish changed bytes under the old v1.1.8 / VC211 identity.
- Do not request another reboot merely to prove the hotfix unless a later symptom makes reboot persistence the active blocker.

## 14. NEW CHAT / CHAT-LIMIT BOOTSTRAP

If a DJAEGER AI chat reaches the conversation limit, or the user starts a new chat and only says something short such as:
- "Lanjutkan DJAEGER GAMING"
- "Lanjutkan DJAEGER AI GAMING"
- "Lanjutkan dari terakhir"
- "Teruskan proyek DJAEGER"
- "Lanjutkan"

then ChatGPT should NOT ask the user to reconstruct the project from memory.

Bootstrap procedure:
1. Identify that the requested project is DJAEGER GAMING.
2. Read this `CHATGPT.md` first.
3. **Do not answer "latest version", "latest pair", "what is installed", or equivalent from model memory.**
4. Read the latest relevant repository/artifact/device evidence needed for the unresolved task.
5. Continue from **CURRENT VERIFIED STATE**, **ACTIVE BLOCKERS**, and **NEXT ACTION**.
6. Do not repeat work already marked completed.
7. If this file is stale compared with newer verified repository/device evidence, reconcile it and update this file before continuing.
8. If the user names another DJAEGER project, use that project's own memory file instead; never cross-contaminate projects.
9. If this file cannot be fetched, explicitly report that the SSOT could not be read and do not guess the current pair/state.

User fallback:
- The user does not need to remember a special command.
- A short instruction such as **"Lanjutkan DJAEGER GAMING"** or **"Lanjutkan DJAEGER AI GAMING"** is sufficient when repository access is available.
- If repository access is unavailable in a future session, explicitly say that the project memory could not be fetched rather than guessing.


## 13. CHANGELOG
### 2026-09-23 — Post-install live verification + HOTFIX1
- User installed and rebooted DJAEGER GAMING v1.1.8 V3.4 FINAL.
- Real device proves APK VC112 / module VC211 / version `1.1.8-v3.4-final`.
- Control Center handshake: `PAIR_VERIFIED=YES`.
- Memory: `MAX_BYTES=104857600`; live execution range source: `LIVE_POLICY_BOUNDS`.
- Railway accepted fresh module VC211 telemetry over HTTP 200 after installation and during real game workload `sts.al`.
- Credential continuity (nonsecret): Gemini key count 4, Hermes access key present, local neuron estimate present.
- Post-install defect found: original `service.sh` did not start `hermes_thought_worker.sh` after reboot; missing knowledge TSV also generated repeated worker errors.
- Live HOTFIX1: patched installed service lifecycle and initialized persistent knowledge TSV. Worker binary was restored to the original artifact after an unsuccessful inline-edit attempt, then started cleanly.
- V3.4 worker verified live: one singleton owner, HERMES_LOCAL, advancing AT/heartbeat, `LAST_STAGE=PUBLISHED`, `LAST_ERROR=NONE`, error log no longer grows.
- Source HOTFIX1 branch: `djaeger-gaming-v3.4-postinstall-hotfix1`.
- Source commits: lifecycle `ff7123ad7318fca34f6ef8ca2b413e33ea2332f5`; first-boot knowledge init `3c6e816e1639766bf082d940f2f73ac24245c800`.
- Audit head `3165fe4bff0211cf933a54f54fa52df22af88829`; Actions run `35876436725` SUCCESS.
- Device status promoted to `v1.1.8-v3.4-final+POSTINSTALL_HOTFIX1`.
- Safe-reject path verified after HOTFIX1: Shadow rejected a real candidate with `human_comfort_contract_failed_POWER_EFFICIENCY`; executor stayed IDLE as required.
- Original v1.1.8 ZIP remains a historical build artifact with a known lifecycle gap; do not reinstall it as if HOTFIX1 were included.

### 2026-09-23 — DJAEGER GAMING v1.1.8 V3.4 FINAL pair built
- Final identity: module VC211 / APK VC112 / version `1.1.8-v3.4-final`.
- Canonical files: `DJAEGER-GAMING-Module-v1.1.8-V3.4-FINAL.zip` and `DJAEGER-GAMING-v1.1.8-V3.4-FINAL.apk`.
- Final source commit: `fb2c41009e20416deff88523c84fe02072b33fb4`.
- Final-pair workflow run `35873269162`: SUCCESS.
- Artifact ID `10757025416`; archive digest `sha256:4464b8d2ada6d9d35b8be6f70a3f27d2b46a6967bfcd2267db8423abb5d05635`.
- APK SHA-256: `97bc32bb68c93fa8ac6527a86bd18bd0a1b4752b13b0a65192f6fc3be03cca37`.
- Module SHA-256: `7c7fcd05682b7543f9668c7b58c698973cba8a47b5f9127fa677bf92b683a5d8`.
- APK signer SHA-256: `bb3f854a7763b5f9a5c87d279e3cbf1c538b03d9ab120f6b375a97c8d06b0269`; v2/v3 verification PASS.
- Signing continuity warning: new signer; drop-in update over older APK is not guaranteed.
- Pair remains build/offline verified, not live-device verified.
- v1.1.7 adaptivefix is superseded as canonical artifact identity.

### 2026-09-23 — V3.4 final consolidation audit PASS
- Preserved detached final source commit `8183a91c088721a14e28bcf82e2009a2f67b737f` on branch `djaeger-gaming-v3.4-final-consolidation`.
- Added audit-only CI gate; no APK/module packaging was performed by the audit workflow.
- Initial audit run `35871357452` failed only because isolation scanner matched the comment substring `ONE HERMES worker` as `hermes work`; no DJAEGER Work source contamination was found.
- Reworded that comment only; runtime logic was unchanged.
- Final audit commit: `2d6dc1d1183dbab5ed47451425f73f1f1249b5f4`.
- GitHub Actions run `35871582592`: SUCCESS.
- PASS gates: source isolation, shell syntax, V3.4 lifecycle + Shadow contract, full module contract/fake-sysfs regressions, Android release unit tests.
- Together with the prior real-device `V3_4_GAME_VERIFY=PASS`, the source/runtime consolidation gate is now clean.
- NEXT: determine exact final source version identity, then build exactly one matched module + APK pair. Do not install/promote it as live until post-install device evidence passes.


### 2026-09-23 — Recovered final chat-limit checkpoint
- Recovered the last DJAEGER GAMING runtime state from the chat that hit its limit.
- Real-device checkpoint: `V3_4_GAME_VERIFY=PASS`.
- `HERMES_ACTIVE_SOURCE=HERMES_LOCAL`.
- `THOUGHT_WORKER_VERSION=ONE_HERMES_THOUGHT_V3_4`.
- `PROGRESS=STEADY`.
- `FRAME_CLASS=FRAME_SMOOTH`.
- Evidence line: `shadow:WAITING,executor:IDLE,intent:NONE,progress:STEADY`.
- Restored the true unfinished task: final combined audit + consolidation of proven V3/V3.4 runtime patches into source, with service/Shadow lifecycle verification.
- Preserved the prior constraint: no new final module/APK build until runtime/source consolidation is complete.

### 2026-09-23 — SSOT hardening / canonical pair repair
- Recorded the canonical v1.1.7 adaptivefix FINAL APK/module pair and exact SHA-256 values.
- Separated `LATEST_CANONICAL_ARTIFACT_PAIR` from `LATEST_DEVICE_VERIFIED_PAIR`.
- Marked real-device installed/live state as unknown until proven by device evidence.
- Added a hard bootstrap rule forbidding answers about latest/current versions from model memory.
- Added explicit fail-closed behavior: if `CHATGPT.md` cannot be read, report that and do not guess.
- Corrected the stale blocker that previously claimed the canonical pair had not been recorded.

### 2026-09-23 — Alias clarification
- Accepted both `DJAEGER GAMING` and `DJAEGER AI GAMING` as names for the current project.
- Plain `DJAEGER AI` remains legacy/ambiguous and should not be assumed to mean the current project without context.


### 2026-09-23 — Rename
- Canonical project name changed from **DJAEGER AI / DJAEGER AI Gaming** to **DJAEGER GAMING**.
- Legacy names remain only for historical references.
- New sessions should use **"Lanjutkan DJAEGER GAMING"**.


### 2026-09-23
- Created `CHATGPT.md` as persistent project memory for DJAEGER GAMING.
- Added project isolation rules.
- Added real-device verification rules.
- Added the historical v1.1.7 adaptivefix signing/live-validation checkpoint.
- Added adaptive-engine direction and session handover workflow.
