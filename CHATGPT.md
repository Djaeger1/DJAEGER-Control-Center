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

## 4. HISTORICAL VERIFIED CHECKPOINT — v1.1.7 ADAPTIVEFIX

This is a **historical checkpoint from an important prior chat**, not an assertion that it is the latest installed release today.

Artifacts discussed:
- APK: `DJAEGER-AI-Adaptive-v1.1.7-adaptivefix-FINAL.apk`
- Module: `DJAEGER-AI-Adaptive-Module-v1.1.7-adaptivefix-FINAL.zip`

Important state at that checkpoint:
- The final pair had been built/audited as artifacts.
- The final APK was signed with an **ephemeral build key**.
- Therefore direct update compatibility over the previously installed APK was **not guaranteed** unless the signer matched.
- The pair was **not allowed to be called live-verified merely because the build passed**.
- Post-install validation on the actual phone was still required.
- The previously observed runtime on the phone remained the only live state that had been demonstrated at that point.

Rule derived from this checkpoint:
- **BUILD SUCCESS ≠ DEVICE SUCCESS**
- **ARTIFACT VALID ≠ INSTALLED RUNTIME VALID**
- Require post-install evidence before promoting a new pair to "verified live".

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

This section must only contain facts verified from the current project/repository/device evidence.

- Project memory file initialized on **2026-09-23**.
- Repository: `Djaeger1/DJAEGER-Control-Center`.
- The v1.1.7 adaptivefix state above is retained as a historical handover checkpoint.
- The latest installed device state / latest release must be re-verified from live project evidence before being written here.

## 11. ACTIVE BLOCKERS

- Latest real-device state is not yet recorded in this file.
- Latest canonical APK/module pair is not yet recorded in this file.
- Latest commit/deployment/runtime evidence must be reconciled before this file can represent the full current state.

## 12. NEXT ACTION

On the next DJAEGER GAMING work session:
- Read this file first.
- Audit the repository and the latest real-device/runtime evidence.
- Replace the placeholders in **CURRENT VERIFIED STATE** and **ACTIVE BLOCKERS** with the latest proven state.
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
3. Read the latest relevant repository state / commit / runtime evidence needed for the unresolved task.
4. Continue from **CURRENT VERIFIED STATE**, **ACTIVE BLOCKERS**, and **NEXT ACTION**.
5. Do not repeat work already marked completed.
6. If this file is stale compared with newer verified repository/device evidence, reconcile it and update this file before continuing.
7. If the user names another DJAEGER project, use that project's own memory file instead; never cross-contaminate projects.

User fallback:
- The user does not need to remember a special command.
- A short instruction such as **"Lanjutkan DJAEGER GAMING"** or **"Lanjutkan DJAEGER AI GAMING"** is sufficient when repository access is available.
- If repository access is unavailable in a future session, explicitly say that the project memory could not be fetched rather than guessing.


## 13. CHANGELOG
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
