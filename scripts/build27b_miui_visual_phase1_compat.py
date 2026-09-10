from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 27', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.1-rc-miui-visual-phase1"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.0 RC • MIUI CONSTRUCTION • REALTIME 1s',
                'GAMING TURBO • v0.11.1 RC • MIUI VISUAL PHASE 1 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.0 RC', 'DJAEGER v0.11.1 RC')
m.write_text(ms)

# Preserve the intended Phase 1 palette, but only replace anchors Build26
# actually emits. Missing optional visual anchors are not treated as runtime
# failures because Build28 replaces the panel hierarchy in the next stage.
for old, new in {
    'private val accent = Color.rgb(20, 173, 255)': 'private val accent = Color.rgb(45, 190, 255)',
    'private val accentSoft = Color.rgb(41, 126, 190)': 'private val accentSoft = Color.argb(150, 72, 148, 191)',
    'private val dark = Color.argb(244, 5, 13, 22)': 'private val dark = Color.argb(232, 7, 10, 14)',
    'private val panel = Color.argb(250, 8, 18, 30)': 'private val panel = Color.argb(238, 11, 15, 20)',
    'private val card = Color.argb(247, 13, 27, 42)': 'private val card = Color.argb(220, 22, 28, 36)',
    'private val muted = Color.rgb(157, 181, 204)': 'private val muted = Color.rgb(166, 177, 188)',
    'private val white = Color.rgb(240, 246, 252)': 'private val white = Color.rgb(246, 248, 250)',
}.items():
    if old not in s:
        raise SystemExit(f'Build27b: required Build26 palette anchor missing: {old}')
    s = s.replace(old, new, 1)

old_handle = '''    private fun buildHandle(): View {
        val handle = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(235, 5, 20, 35), accent, 0)
            setPadding(dp(8), dp(13), dp(8), dp(13))
        }
        handle.addView(TextView(this).apply {
            text = "ᛉ"
            textSize = 19f
            gravity = Gravity.CENTER
            setTextColor(accent)
            typeface = Typeface.DEFAULT_BOLD
        })
        handle.addView(TextView(this).apply {
            text = "⋮"
            textSize = 18f
            gravity = Gravity.CENTER
            setTextColor(muted)
            setPadding(0, dp(5), 0, 0)
        })
        attachHandleGesture(handle)
        return handle
    }
'''
new_handle = '''    private fun buildHandle(): View {
        val handle = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(222, 10, 14, 18), Color.argb(115, 125, 210, 248), 18)
            setPadding(dp(5), dp(17), dp(5), dp(17))
            minimumWidth = dp(22)
        }
        handle.addView(View(this).apply {
            background = rounded(Color.argb(235, 202, 236, 252), Color.TRANSPARENT, 18)
        }, LinearLayout.LayoutParams(dp(3), dp(28)))
        attachHandleGesture(handle)
        return handle
    }
'''
if old_handle not in s:
    raise SystemExit('Build27b: Build26 handle block missing')
s = s.replace(old_handle, new_handle, 1)

required = [
    'private fun buildPanel(extended: Boolean): View {',
    'private fun updateOverlayContent()',
    'private val pollRunnable: Runnable = object : Runnable',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'launchMiuiFreeform', 'djaeger-ai mode',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build27b regression: {marker}')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build27b regression: forbidden behavior present: {forbidden}')

h.write_text(s)
print('Build 27b compatibility visual phase applied: Build26-aligned handle/palette, behavior preserved')
