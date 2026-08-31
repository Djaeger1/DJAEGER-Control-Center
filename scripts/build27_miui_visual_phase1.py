from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

# Phase 1 is intentionally visual-only. It must not change telemetry, polling,
# session detection, freeform behavior, root commands, or DJAEGER authority.
# The goal is to move the shell closer to MIUI Game Turbo hierarchy without
# introducing new runtime behavior.

# Version bump for branch validation.
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

# MIUI-like visual palette: charcoal glass panel, cool cyan accent, softer borders.
replacements = {
    '    private val accent = Color.rgb(20, 173, 255)\n':
        '    private val accent = Color.rgb(45, 190, 255)\n',
    '    private val accentSoft = Color.rgb(41, 126, 190)\n':
        '    private val accentSoft = Color.argb(150, 72, 148, 191)\n',
    '    private val dark = Color.argb(244, 5, 13, 22)\n':
        '    private val dark = Color.argb(232, 7, 10, 14)\n',
    '    private val panel = Color.argb(250, 8, 18, 30)\n':
        '    private val panel = Color.argb(238, 11, 15, 20)\n',
    '    private val card = Color.argb(247, 13, 27, 42)\n':
        '    private val card = Color.argb(220, 22, 28, 36)\n',
    '    private val muted = Color.rgb(157, 181, 204)\n':
        '    private val muted = Color.rgb(166, 177, 188)\n',
    '    private val white = Color.rgb(240, 246, 252)\n':
        '    private val white = Color.rgb(246, 248, 250)\n',
}
for old, new in replacements.items():
    if old not in s:
        raise SystemExit(f'Build27: palette anchor missing: {old!r}')
    s = s.replace(old, new, 1)

# Slim side handle closer to MIUI Game Turbo's understated edge tab.
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
    raise SystemExit('Build27: buildHandle block changed; refusing blind patch')
s = s.replace(old_handle, new_handle, 1)

# Panel shell: wider radius, subtler border/padding like the MIUI floating toolbox.
old_panel_shell = '''        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(panel, accentSoft, 16)
            setPadding(dp(11), dp(9), dp(11), dp(11))
        }
'''
new_panel_shell = '''        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(panel, Color.argb(92, 124, 192, 224), 22)
            setPadding(dp(14), dp(11), dp(14), dp(13))
            minimumWidth = dp(292)
        }
'''
if old_panel_shell not in s:
    raise SystemExit('Build27: panel shell anchor missing')
s = s.replace(old_panel_shell, new_panel_shell, 1)

# Header hierarchy: compact Game Turbo title with DJAEGER identity retained.
old_title = '''        header.addView(TextView(this).apply {
            text = "ᛉ  DJAEGER AI\n     GAME TURBO"
            textSize = 11f; setTextColor(white); typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
'''
new_title = '''        header.addView(TextView(this).apply {
            text = "DJAEGER  GAME TURBO"
            textSize = 12f
            letterSpacing = 0.04f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
'''
if old_title not in s:
    raise SystemExit('Build27: header title anchor missing')
s = s.replace(old_title, new_title, 1)

# Profile row becomes a restrained status strip instead of a dashboard card.
old_profile = '''        val profile = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            background = rounded(card, Color.TRANSPARENT, 9); setPadding(dp(8), dp(6), dp(8), dp(6))
        }
        profile.addView(TextView(this).apply { text = "Performance"; textSize = 10f; setTextColor(accent) }, LinearLayout.LayoutParams(0, -2, 1f))
        panelMode = TextView(this).apply { text = snapshot.mode; textSize = 10f; setTextColor(accent); setPadding(dp(8), 0, 0, 0) }
'''
new_profile = '''        val profile = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(Color.argb(118, 255, 255, 255), Color.TRANSPARENT, 16)
            alpha = 0.16f
            setPadding(dp(10), dp(6), dp(10), dp(6))
        }
        profile.addView(TextView(this).apply {
            text = "GAME PERFORMANCE"
            textSize = 9f
            letterSpacing = 0.05f
            setTextColor(white)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        panelMode = TextView(this).apply {
            text = snapshot.mode
            textSize = 9f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(8), 0, 0, 0)
        }
'''
if old_profile not in s:
    raise SystemExit('Build27: profile row anchor missing')
s = s.replace(old_profile, new_profile, 1)

# Keep telemetry row compact and visually secondary to the tool strip.
s = s.replace(
    'val metrics = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(3), dp(7), dp(3), dp(6)) }',
    'val metrics = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(2), dp(8), dp(2), dp(8)) }',
    1
)

# Static regression guards. Phase 1 must not alter behavior paths.
required = [
    'private fun updateOverlayContent()',
    'private val pollRunnable: Runnable = object : Runnable',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'launchMiuiFreeform',
    'djaeger-ai mode',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build27 regression: required marker missing: {marker}')

for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build27 regression: forbidden behavior introduced/present: {forbidden}')

h.write_text(s)
print('Build 27 MIUI visual phase 1 applied: shell-only, behavior preserved')
