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

## 4. CURRENT CANONICAL ARTIFACT PAIR — v1.1.7 ADAPTIVEFIX

This is the **current canonical artifact pair recorded by project memory** as of 2026-09-23. It is an artifact-level identity, **not** proof that this exact pair is currently installed and live-verified on the phone.

Canonical pair:
- APK: `DJAEGER-AI-Adaptive-v1.1.7-adaptivefix-FINAL.apk`
- APK SHA-256: `d4792eeb3fa04e9ca9a9cf35a423ee0a8f22e1bdfad39e219dbcc3c08ae92be0`
- Module: `DJAEGER-AI-Adaptive-Module-v1.1.7-adaptivefix-FINAL.zip`
- Module SHA-256: `be21b78431e92909ff7bc78a9ffd9d07ab6c78bd6d83f38fe7a4fe22392ca6e2`

Important state:
- This pair exists as built project artifacts and has a matching checksum manifest in the ChatGPT Library.
- The final APK was signed with an **ephemeral build key**.
- Therefore direct update compatibility over a previously installed APK is **not guaranteed** unless the signer matches.
- The pair must **not** be called live-verified merely because the artifacts exist or the build passed.
- Post-install validation on the actual phone is still required before `LATEST_DEVICE_VERIFIED_PAIR` can be populated.

Hard rule:
- **BUILD SUCCESS ≠ DEVICE SUCCESS**
- **ARTIFACT VALID ≠ INSTALLED RUNTIME VALID**
- Require post-install evidence before promoting a pair to `VERIFIED_LIVE`.

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

LATEST_CANONICAL_ARTIFACT_PAIR=v1.1.7-adaptivefix-FINAL
LATEST_CANONICAL_APK=DJAEGER-AI-Adaptive-v1.1.7-adaptivefix-FINAL.apk
LATEST_CANONICAL_APK_SHA256=d4792eeb3fa04e9ca9a9cf35a423ee0a8f22e1bdfad39e219dbcc3c08ae92be0
LATEST_CANONICAL_MODULE=DJAEGER-AI-Adaptive-Module-v1.1.7-adaptivefix-FINAL.zip
LATEST_CANONICAL_MODULE_SHA256=be21b78431e92909ff7bc78a9ffd9d07ab6c78bd6d83f38fe7a4fe22392ca6e2
CANONICAL_ARTIFACT_STATUS=VERIFIED_ARTIFACT_IDENTITY

LATEST_DEVICE_VERIFIED_PAIR=UNKNOWN
LATEST_DEVICE_VERIFIED_AT=UNKNOWN
LATEST_DEVICE_RUNTIME_STATUS=NOT_RECONCILED
```

Interpretation:
- The canonical artifact pair is now explicitly recorded and must not be guessed from memory.
- `LATEST_DEVICE_VERIFIED_PAIR=UNKNOWN` means there is currently **no project-memory proof** that v1.1.7, or any later pair, is the pair presently installed and verified live on the phone.
- Do not silently copy `LATEST_CANONICAL_ARTIFACT_PAIR` into `LATEST_DEVICE_VERIFIED_PAIR`.
- Real-device evidence is required before those fields may be changed.

## 11. ACTIVE BLOCKERS

- Latest real-device installed pair is not yet recorded with live evidence.
- Latest real-device runtime state is not yet reconciled into this file.
- The canonical artifact pair **is now recorded**; do not list it as unknown again unless newer artifact evidence supersedes it.
- Any newer repository/device evidence must be reconciled before promoting a new pair or runtime state.

## 12. NEXT ACTION

On the next DJAEGER GAMING work session:
- Read this file **before answering version/state questions**.
- Treat v1.1.7 adaptivefix FINAL as the current canonical artifact pair unless newer artifact evidence is found.
- Verify the actually installed APK/module pair from real-device evidence.
- Reconcile runtime evidence and populate `LATEST_DEVICE_VERIFIED_PAIR`, `LATEST_DEVICE_VERIFIED_AT`, and `LATEST_DEVICE_RUNTIME_STATUS` only when proven.
- Then continue only from the remaining unresolved issue.


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
