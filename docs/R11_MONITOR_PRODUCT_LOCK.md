# DJAEGER Monitor r11 — Product Lock

The next Android application is a normal standalone monitoring app. It is NOT a game launcher, HUD, overlay, MIUI Game Turbo integration, freeform launcher, floating window controller, or game opener.

## Remove from r11 product surface
- HUD and floating telemetry overlay
- launcher/game launcher
- MIUI Game Turbo integration
- freeform/multiwindow launch actions
- game launch buttons
- overlay permission requirement when it exists only for HUD
- launcher/freeform-specific services, receivers, shortcuts and UI

`window_mode=MULTIWINDOW` may still be displayed as read-only telemetry because it describes DJAEGER runtime state. The app must never create or request that window mode.

## Keep
- standalone dashboard activity
- coherent runtime telemetry
- game/session/window status as information
- CPU/GPU/skin/battery/FPS/frame-time monitoring
- read-only network intelligence
- Local AI/Gemini status
- Gemini quota/backoff/auth monitoring
- Strategy Composition as published by DJAEGER
- Strategy Result validation/apply/readback/outcome monitoring
- learning/confidence/promotion monitoring
- Root Authority state
- manual refresh that only rereads monitoring state

## Authority boundary
The app cannot control DJAEGER, hardware, game launch/window behavior, Gemini requests, API keys, services, networking or system tuning.

## Build identity
Target: `v0.12.1-r11-monitor-only`.

This file supersedes earlier r11 requirements that said existing HUD/freeform/MIUI launcher behavior must be preserved.
