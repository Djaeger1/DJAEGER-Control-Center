from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 31', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.5-rc-game-session-scene-phase5"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.4 RC • MIUI FREEFORM PHASE 4 • REALTIME 1s',
                'GAMING TURBO • v0.11.5 RC • SESSION + SCENE PHASE 5 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.4 RC', 'DJAEGER v0.11.5 RC')
m.write_text(ms)

# Scene model is deliberately conservative. CPU_BOUND/GPU_BOUND are NOT emitted
# until load/utilisation sources are integrated in a later phase.
anchor = '    private enum class HudState { HANDLE, PANEL, EXTENDED }\n\n'
if anchor not in s:
    raise SystemExit('Build31: HudState anchor missing')
s = s.replace(anchor, anchor + '''    private enum class SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, THERMAL_BOUND }\n\n    private data class SceneAssessment(\n        val state: SceneState = SceneState.UNKNOWN,\n        val confidence: Int = 0,\n        val source: String = "INSUFFICIENT_SIGNALS"\n    )\n\n''', 1)

old_runtime = '''    private data class RuntimeSnapshot(\n        val fps: String = "--",\n        val frameMs: String = "--",\n        val cpuTemp: String = "--",\n        val gpuTemp: String = "--",\n        val mode: String = "AUTO",\n        val game: String = "NA",\n        val window: String = "INACTIVE",\n        val session: String = "INACTIVE"\n    )\n'''
new_runtime = '''    private data class RuntimeSnapshot(\n        val fps: String = "--",\n        val frameMs: String = "--",\n        val cpuTemp: String = "--",\n        val gpuTemp: String = "--",\n        val mode: String = "AUTO",\n        val game: String = "NA",\n        val window: String = "INACTIVE",\n        val session: String = "INACTIVE",\n        val scene: SceneAssessment = SceneAssessment()\n    )\n'''
if old_runtime not in s:
    raise SystemExit('Build31: RuntimeSnapshot anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

# Session continuity state. A short hold only covers the transition while a
# verified freeform app takes focus; it is not a permanent fake ACTIVE state.
anchor = '    private var floatingExpanded = true\n'
if anchor not in s:
    raise SystemExit('Build31: continuity field anchor missing')
s = s.replace(anchor, anchor + '''    private var lastConfirmedGameAt = 0L\n    private var freeformTransitionHoldUntil = 0L\n''', 1)

anchor = '    private var panelSession: TextView? = null\n'
if anchor not in s:
    raise SystemExit('Build31: panel field anchor missing')
s = s.replace(anchor, anchor + '    private var panelScene: TextView? = null\n', 1)

# Replace session-state application with transition-aware continuity.
start = s.find('    private fun applySessionState(active: Boolean) {')
end = s.find('\n    private fun isGameSessionActive(state: RuntimeSnapshot): Boolean {', start)
if start < 0 or end < 0:
    raise SystemExit('Build31: applySessionState boundaries missing')
new_apply = r'''    private fun applySessionState(active: Boolean) {
        val now = android.os.SystemClock.elapsedRealtime()
        if (active) lastConfirmedGameAt = now
        val heldByFreeformTransition = gameSessionActive && now < freeformTransitionHoldUntil
        val effectiveActive = active || heldByFreeformTransition

        if (!effectiveActive) {
            suppressedForCurrentSession = false
            if (gameSessionActive) {
                gameSessionActive = false
                freeformTransitionHoldUntil = 0L
                removeOverlay()
            }
            return
        }
        gameSessionActive = true
        if (suppressedForCurrentSession || !Settings.canDrawOverlays(this)) return
        if (overlayView == null) {
            hudState = HudState.HANDLE
            showOverlay()
        } else {
            updateOverlayContent()
        }
    }
'''
s = s[:start] + new_apply + s[end:]

# Add a signal-based scene classifier before parseSnapshot.
parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build31: parseSnapshot anchor missing')
classifier = r'''    private fun assessScene(
        runtime: Map<String, String>,
        fps: Double?,
        frameMs: Double?,
        jankPct: Double?,
        cpuTemp: Double?,
        gpuTemp: Double?
    ): SceneAssessment {
        val cause = listOfNotNull(runtime["cause"], runtime["thermal_state"], runtime["state_reason"])
            .joinToString(" ").lowercase(Locale.US)
        if ("thermal" in cause || "overheat" in cause || "throttle" in cause) {
            return SceneAssessment(SceneState.THERMAL_BOUND, 95, "RUNTIME_THERMAL_SIGNAL")
        }

        // No CPU/GPU-bound claim is made here because v0.11.5 does not yet have
        // trustworthy utilisation data from KGSL/cpu scheduler sources.
        if (fps != null && frameMs != null) {
            if ((jankPct ?: 0.0) >= 20.0 || frameMs >= 35.0) {
                return SceneAssessment(SceneState.HIGH_LOAD, 72, "FRAME_TIME_JANK")
            }
            if (fps < 18.0 && frameMs >= 45.0) {
                return SceneAssessment(SceneState.LOADING_CANDIDATE, 45, "LOW_FPS_LONG_FRAME")
            }
            if (fps >= 24.0 && frameMs in 4.0..42.0) {
                return SceneAssessment(SceneState.GAMEPLAY, 68, "ACTIVE_FRAME_STREAM")
            }
        }
        // Temperatures alone never identify a scene; they only support telemetry.
        @Suppress("UNUSED_VARIABLE") val tempsObserved = cpuTemp != null || gpuTemp != null
        return SceneAssessment(SceneState.UNKNOWN, 20, "INSUFFICIENT_SIGNALS")
    }

'''
s = s.replace(parse_anchor, classifier + parse_anchor, 1)

# Extend CSV parsing with jank and return SceneAssessment.
old_csv = '''        val fps = liveFps ?: csvNumber(10)\n        val frame = liveFrame ?: csvNumber(9)\n        val cpu = cpuNow ?: csvNumber(1)\n        val gpu = gpuNow ?: csvNumber(2)\n'''
new_csv = '''        val fps = liveFps ?: csvNumber(10)\n        val frame = liveFrame ?: csvNumber(9)\n        val jank = csvNumber(11)\n        val cpu = cpuNow ?: csvNumber(1)\n        val gpu = gpuNow ?: csvNumber(2)\n'''
if old_csv not in s:
    raise SystemExit('Build31: CSV parsing anchor missing')
s = s.replace(old_csv, new_csv, 1)

old_return = '        return RuntimeSnapshot(one(fps), one(frame), temp(cpu), temp(gpu), mode.uppercase(Locale.US), game, window, session)\n'
new_return = '''        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu)\n        return RuntimeSnapshot(\n            one(fps), one(frame), temp(cpu), temp(gpu), mode.uppercase(Locale.US),\n            game, window, session, scene\n        )\n'''
if old_return not in s:
    raise SystemExit('Build31: RuntimeSnapshot return anchor missing')
s = s.replace(old_return, new_return, 1)

# In-place HUD scene text. No WindowManager rebuild from polling.
s = s.replace('        panelMode?.text = snapshot.mode\n        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n',
'''        panelMode?.text = snapshot.mode\n        panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"\n        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n''', 1)
s = s.replace('        panelFps = null; panelCpu = null; panelGpu = null; panelMode = null; panelSession = null\n',
              '        panelFps = null; panelCpu = null; panelGpu = null; panelMode = null; panelSession = null; panelScene = null\n', 1)

# Add scene indicator above session footer in the panel.
old_session = '''        panelSession = TextView(this).apply {\n            text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n            textSize = 8f\n            setTextColor(muted)\n            gravity = Gravity.CENTER\n            setPadding(dp(3), dp(8), dp(3), dp(2))\n        }\n        box.addView(panelSession)\n'''
new_session = '''        panelScene = TextView(this).apply {\n            text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"\n            textSize = 8f\n            setTextColor(accent)\n            gravity = Gravity.CENTER\n            setPadding(dp(3), dp(8), dp(3), 0)\n        }\n        box.addView(panelScene)\n        panelSession = TextView(this).apply {\n            text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n            textSize = 8f\n            setTextColor(muted)\n            gravity = Gravity.CENTER\n            setPadding(dp(3), dp(3), dp(3), dp(2))\n        }\n        box.addView(panelSession)\n'''
if old_session not in s:
    raise SystemExit('Build31: panel session anchor missing')
s = s.replace(old_session, new_session, 1)

# Verified freeform gets a bounded transition hold so the game session is not
# torn down merely because the floating app temporarily becomes foreground.
old_confirm = '''                if (state == FreeformState.FREEFORM || state == FreeformState.MINI_FREEFORM) {\n                    hudState = HudState.HANDLE\n                    rebuildOverlayKeepingPosition()\n                }\n'''
new_confirm = '''                if (state == FreeformState.FREEFORM || state == FreeformState.MINI_FREEFORM) {\n                    freeformTransitionHoldUntil = android.os.SystemClock.elapsedRealtime() + 8_000L\n                    hudState = HudState.HANDLE\n                    rebuildOverlayKeepingPosition()\n                }\n'''
if old_confirm not in s:
    raise SystemExit('Build31: freeform confirmation anchor missing')
s = s.replace(old_confirm, new_confirm, 1)

required = [
    'SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, THERMAL_BOUND }',
    'SceneAssessment(', 'assessScene(', 'csvNumber(11)',
    'freeformTransitionHoldUntil', '8_000L',
    'FreeformState.FREEFORM', 'FreeformState.MINI_FREEFORM',
    'private fun updateOverlayContent()', 'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")',
    'djaeger-ai mode'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build31 regression: required marker missing: {marker}')

# CPU_BOUND/GPU_BOUND are intentionally not emitted until load sources exist.
if 'SceneState.CPU_BOUND' in s or 'SceneState.GPU_BOUND' in s:
    raise SystemExit('Build31: unsupported bottleneck classification introduced')
apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body:
    raise SystemExit('Build31: in-place update missing from session path')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build31: anti-flicker invariant broken: {forbidden_call}')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build31: forbidden unrelated mutation present: {forbidden}')

h.write_text(s)
print('Build 31 phase 5 applied: session continuity + conservative scene intelligence')
