from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 37', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.12.1-rc-hardware-overlay-fix"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.12.0 RC • STAGE 12 MATURITY • REALTIME 1s',
                'GAMING TURBO • v0.12.1 RC • HARDWARE OVERLAY FIX • REALTIME 1s')
ms = ms.replace('DJAEGER v0.12.0 RC', 'DJAEGER v0.12.1 RC')
m.write_text(ms)

# Hardware finding: panel drag listener installed on the root after buildHandle()
# replaced the handle's own touch listener. Never attach panel drag to HANDLE.
old_show = '''        attachPanelDrag(view, params)\n        overlayView = view\n'''
new_show = '''        if (hudState != HudState.HANDLE) attachPanelDrag(view, params)\n        overlayView = view\n'''
if old_show not in s:
    raise SystemExit('Build37: showOverlay drag anchor missing')
s = s.replace(old_show, new_show, 1)

# Hardware finding: visually large handle intruded into game. Keep the actual
# overlay narrow and flush to physical edge. Vertical relocation can be added as
# a separate gesture later; horizontal X must stay zero for collapsed handle.
start = s.find('    private fun buildHandle(): View {')
end = s.find('\n    private fun attachHandleGesture(view: View) {', start)
if start < 0 or end < 0:
    raise SystemExit('Build37: buildHandle boundaries missing')
new_handle = r'''    private fun buildHandle(): View {
        val handle = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(196, 8, 12, 16), Color.argb(72, 215, 241, 252), 14)
            setPadding(dp(4), dp(16), dp(4), dp(16))
            minimumWidth = dp(11)
        }
        handle.addView(View(this).apply {
            background = rounded(Color.argb(238, 215, 241, 252), Color.TRANSPARENT, 14)
        }, LinearLayout.LayoutParams(dp(2), dp(29)))
        attachHandleGesture(handle)
        return handle
    }
'''
s = s[:start] + new_handle + s[end:]

# A collapsed handle always returns to the screen edge. This prevents remembered
# panel X offsets from leaving the rail floating inside the game viewport.
old_params = '''            gravity = Gravity.TOP or if (handleOnRight) Gravity.END else Gravity.START\n            x = dp(lastX)\n            y = dp(lastY)\n'''
new_params = '''            gravity = Gravity.TOP or if (handleOnRight) Gravity.END else Gravity.START\n            x = if (hudState == HudState.HANDLE) 0 else dp(lastX)\n            y = dp(lastY)\n'''
if old_params not in s:
    raise SystemExit('Build37: overlay position anchor missing')
s = s.replace(old_params, new_params, 1)

# Do not persist HANDLE x=0 over the remembered panel position when changing
# HANDLE -> PANEL. Preserve Y only and let panel open from edge.
old_rebuild = '''    private fun rebuildOverlayKeepingPosition() {\n        overlayParams?.let { p -> lastX = pxToDp(p.x); lastY = pxToDp(p.y) }\n        showOverlay()\n    }\n'''
new_rebuild = '''    private fun rebuildOverlayKeepingPosition() {\n        overlayParams?.let { p ->\n            if (hudState == HudState.HANDLE) lastX = 0\n            lastY = pxToDp(p.y)\n        }\n        showOverlay()\n    }\n'''
if old_rebuild not in s:
    raise SystemExit('Build37: rebuild position anchor missing')
s = s.replace(old_rebuild, new_rebuild, 1)

# Session runtime must not trust a stale runtime_status ACTIVE forever. Verify
# the package is actually present in current focused/resumed ActivityManager
# state before keeping an overlay alive. No force-stop or process mutation.
old_active = '''    private fun isGameSessionActive(state: RuntimeSnapshot): Boolean {\n        val window = state.window.uppercase(Locale.US)\n        val session = state.session.uppercase(Locale.US)\n        val game = state.game.uppercase(Locale.US)\n        if (window == "ACTIVE" || session == "ACTIVE") return true\n        if (game == "NA" || game == "INACTIVE" || game.isBlank()) return false\n        return window != "INACTIVE"\n    }\n'''
new_active = r'''    private fun isGameSessionActive(state: RuntimeSnapshot): Boolean {
        val window = state.window.uppercase(Locale.US)
        val session = state.session.uppercase(Locale.US)
        val gameRaw = state.game.trim()
        val game = gameRaw.uppercase(Locale.US)
        if (game == "NA" || game == "INACTIVE" || gameRaw.isBlank()) return false

        val runtimeClaimsActive = window == "ACTIVE" || session == "ACTIVE" || window != "INACTIVE"
        if (!runtimeClaimsActive) return false

        // runtime_status may lag behind foreground changes. Confirm the exact
        // package against the current resumed/focused activity before retaining
        // an intrusive overlay. Sanitize because it enters a root read-only grep.
        val pkg = gameRaw.replace(Regex("[^A-Za-z0-9._]"), "")
        if (pkg.isBlank() || !pkg.contains('.')) return runtimeClaimsActive
        val focused = runRoot(
            "dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity' | head -n 8"
        )
        return focused.contains(pkg)
    }
'''
if old_active not in s:
    raise SystemExit('Build37: session detector anchor missing')
s = s.replace(old_active, new_active, 1)

# Freeform hold must only preserve a session while the hold is actually needed;
# a stale game package cannot keep the overlay after the user exits the game.
old_hold = '''        val heldByFreeformTransition = gameSessionActive && now < freeformTransitionHoldUntil\n        val effectiveActive = active || heldByFreeformTransition\n'''
new_hold = '''        val heldByFreeformTransition = gameSessionActive && now < freeformTransitionHoldUntil\n        val effectiveActive = active || heldByFreeformTransition\n'''
if old_hold not in s:
    raise SystemExit('Build37: freeform hold anchor missing')
# Keep bounded hold semantics; hardware bug was stale ACTIVE verification, not hold duration.

required = [
    'if (hudState != HudState.HANDLE) attachPanelDrag(view, params)',
    'x = if (hudState == HudState.HANDLE) 0 else dp(lastX)',
    'attachHandleGesture(handle)',
    'mResumedActivity|topResumedActivity|ResumedActivity',
    'focused.contains(pkg)',
    'removeOverlay()',
    'private fun updateOverlayContent()',
    'dumpsys SurfaceFlinger --latency',
    'DJAEGER_LOCAL_POLICY_V1', 'DJAEGER_POLICY_OUTCOME_V1',
    'PRE_DISPATCH_BASELINE', 'POST_APPLY_OBSERVING',
    'readFreeformState(pkg)',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build37 regression: required marker missing: {marker}')

# Critical hardware-validation invariants.
show_body = s.split('private fun showOverlay()',1)[1].split('private fun rebuildOverlayKeepingPosition()',1)[0]
if 'attachPanelDrag(view, params)' in show_body and 'hudState != HudState.HANDLE' not in show_body:
    raise SystemExit('Build37: handle touch listener can still be overwritten')
handle_body = s.split('private fun buildHandle()',1)[1].split('private fun attachHandleGesture',1)[0]
if 'minimumWidth = dp(28)' in handle_body or 'setPadding(dp(8)' in handle_body:
    raise SystemExit('Build37: intrusive Stage3 handle dimensions remain')
update_ui = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_ui:
        raise SystemExit(f'Build37 anti-flicker regression: {forbidden_call}')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build37 unrelated mutation regression: {forbidden}')

h.write_text(s)
print('Build 37 hardware overlay fix applied: handle touch ownership + edge flush + focused-game exit verification')
