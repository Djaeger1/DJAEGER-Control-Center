# r78 Control Center UI acceptance gates

1. Runtime root is `/data/adb/djaeger_ai`.
2. IDLE + Root Authority RESTORED never displays a historical envelope as currently applied.
3. ACTIVE `sts.al` + MULTIWINDOW remains an active game session.
4. Strategy Composition is empty-state when `gemini_strategy_formula.env` is absent; no guessed clocks/governors.
5. Strategy Result stages are sourced only from `gemini_strategy_result.env`; proposal never implies applied/readback verified.
6. Local AI fallback remains visible and healthy when Gemini returns 429.
7. Gemini HTTP, resync, and server interaction states are presented independently.
8. 429 never triggers automatic key/account rotation from the UI.
9. Key values are masked; manual selection is explicit.
10. Network metrics remain labeled read-only; Control Center has no route/DNS/firewall/proxy mutation.
11. FPS/frame telemetry is not labeled live-verified without verified producer provenance.
12. Stale/missing files render stale/unavailable instead of carrying forward previous values.
13. Control Center performs no direct sysfs/thermal/CPU/GPU writes.
14. Existing HUD/freeform/MIUI launcher behavior must regress cleanly.
15. Build is not promoted as stable until these gates and APK build checks pass.
