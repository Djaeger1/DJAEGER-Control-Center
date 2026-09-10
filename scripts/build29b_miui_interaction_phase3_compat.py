from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 29', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.3-rc-miui-interaction-phase3"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.2 RC • MIUI PANEL PHASE 2 • REALTIME 1s',
                'GAMING TURBO • v0.11.3 RC • MIUI INTERACTION PHASE 3 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.2 RC', 'DJAEGER v0.11.3 RC')
m.write_text(ms)

# Safe visual/interactions that have stable Stage2 anchors.
s = s.replace('minimumWidth = dp(318)', 'minimumWidth = dp(336)', 1)
s = s.replace('setPadding(dp(14), dp(11), dp(14), dp(13))', 'setPadding(dp(15), dp(10), dp(15), dp(11))', 1)

old_handle = '''        val handle = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(222, 10, 14, 18), Color.argb(115, 125, 210, 248), 18)
            setPadding(dp(5), dp(17), dp(5), dp(17))
            minimumWidth = dp(22)
        }
        handle.addView(View(this).apply {
            background = rounded(Color.argb(235, 202, 236, 252), Color.TRANSPARENT, 18)
        }, LinearLayout.LayoutParams(dp(3), dp(28)))
'''
new_handle = '''        val handle = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(205, 10, 14, 18), Color.argb(90, 125, 210, 248), 18)
            setPadding(dp(8), dp(19), dp(8), dp(19))
            minimumWidth = dp(28)
        }
        handle.addView(View(this).apply {
            background = rounded(Color.argb(238, 215, 241, 252), Color.TRANSPARENT, 18)
        }, LinearLayout.LayoutParams(dp(3), dp(31)))
'''
if old_handle not in s:
    raise SystemExit('Build29b: Stage2 handle anchor missing')
s = s.replace(old_handle, new_handle, 1)

s = s.replace('if (abs(dx) > dp(20) || abs(dy) > dp(20)) moved = true',
              'if (abs(dx) > dp(18) || abs(dy) > dp(18)) moved = true', 1)
s = s.replace('if (abs(dx) > dp(34) && abs(dx) > abs(dy)) {',
              'if (abs(dx) > dp(30) && abs(dx) > abs(dy) * 1.15f) {', 1)

# Build28 already owns the toolbox/floating-app hierarchy. Avoid brittle
# restyling of helper implementations whose formatting differs across baselines.
required = [
    'private fun buildToolGrid(): View {',
    'private fun buildFloatingApps(',
    'private fun updateOverlayContent()',
    'private val pollRunnable: Runnable = object : Runnable',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'launchMiuiFreeform', '__DJAEGER_FREEFORM_CONFIRMED__',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")',
    'runDjaegerBoost()', 'toggleDnd()', 'takeScreenshot()', 'openScreenRecorder()', 'openVoiceChanger()'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build29b regression: {marker}')
apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body or 'rebuildOverlayKeepingPosition()' in apply_body:
    raise SystemExit('Build29b anti-flicker session invariant broken')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build29b forbidden behavior: {forbidden}')

h.write_text(s)
print('Build 29b compatibility interaction phase applied: handle/gesture/proportion polish, Stage2 toolbox preserved')
