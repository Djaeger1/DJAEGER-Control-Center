# r78 Control Center data precedence

Execution presentation precedence:
1. runtime_status active/game/window/user mode
2. root_authority_state actual authority lifecycle
3. gemini_strategy_result.env actual validation/apply/readback/outcome
4. gemini_strategy_formula.env proposal composition
5. cc_snapshot coherent telemetry/brain/network
6. historical/adaptive memory only as explicitly labeled history

Rules:
- IDLE + RESTORED wins over historical envelope content.
- Formula never wins over Strategy Result for actual applied/readback state.
- Gemini server/HTTP metadata never wins over primary reasoning/formula state.
- Missing/stale higher-priority state is displayed as unavailable; do not silently promote historical lower-priority values to current execution.
