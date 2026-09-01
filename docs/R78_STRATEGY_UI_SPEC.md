# Strategy Composition UI specification

## Header
Show source state: GEMINI FORMULA, LOCAL AI FALLBACK, LEARNED LOCAL, or NO FORMULA. This label comes from runtime/module publications, never heuristics.

## Composition
Render concrete published values in grouped rows:
- CPU LITTLE: min / max / governor
- CPU BIG: min / max / governor
- GPU: min / max / governor
- power/thermal/comfort typed fields when present
- burst/lease duration and temporary resource fields when present
- owner mode, profile, game, window/session context
- rationale and confidence when present

Absent fields display `—`; never substitute baseline values into a Gemini formula card.

## Validation pipeline
Render each stage independently:
- PROPOSED
- VALIDATED or REJECTED
- APPLIED
- READBACK VERIFIED or FAILED
- OUTCOME: SUCCESS / MIXED / FAILED / PENDING

Show transaction/session/game/mode binding metadata in an expandable details section.

## Capability integrity
Expose compact trust/freshness indicators for capability generation, provenance, exact OPP evidence and snapshot freshness. Do not call the canonical content signature cryptographic tamper protection.

## Outcome
When available, show actual post-application FPS/frame/skin/power observations and learned-sample/confidence/promotion state. Keep proposal and actual result visually distinct.

## 429 state
When primary Gemini reasoning is quota-limited, show `Gemini quota/backoff — Local AI active` if Local AI is active. Do not display `DJAEGER offline` and do not auto-rotate account/key.
