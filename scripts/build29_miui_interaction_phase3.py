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

# More Game-Turbo-like proportions: wider glass panel and tighter vertical density.
s = s.replace('minimumWidth = dp(318)', 'minimumWidth = dp(336)', 1)
s = s.replace('setPadding(dp(14), dp(11), dp(14), dp(13))', 'setPadding(dp(15), dp(10), dp(15), dp(11))', 1)

# Side handle gets an enlarged invisible touch target while keeping the visible rail slim.
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
    raise SystemExit('Build29: phase2 handle anchor missing')
s = s.replace(old_handle, new_handle, 1)

# Gesture thresholds: deliberate horizontal pull opens panel, tap still opens it.
s = s.replace('if (abs(dx) > dp(20) || abs(dy) > dp(20)) moved = true',
              'if (abs(dx) > dp(18) || abs(dy) > dp(18)) moved = true', 1)
s = s.replace('if (abs(dx) > dp(34) && abs(dx) > abs(dy)) {',
              'if (abs(dx) > dp(30) && abs(dx) > abs(dy) * 1.15f) {', 1)

# Tool buttons: compact rounded tiles with clearer icon hierarchy.
old_tool = '''    private fun toolButton(icon: String, label: String, action: () -> Unit): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; background = rounded(card, Color.TRANSPARENT, 8)
            setPadding(dp(4), dp(5), dp(4), dp(5)); setOnClickListener { action() }
            addView(TextView(this@DjaegerHudService).apply { text = icon; textSize = 17f; gravity = Gravity.CENTER; setTextColor(accent) })
            addView(TextView(this@DjaegerHudService).apply { text = label; textSize = 7f; gravity = Gravity.CENTER; setTextColor(white); maxLines = 1 })
        }
    }
'''
new_tool = '''    private fun toolButton(icon: String, label: String, action: () -> Unit): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(Color.argb(150, 28, 35, 44), Color.argb(48, 255, 255, 255), 15)
            setPadding(dp(5), dp(8), dp(5), dp(7))
            minimumHeight = dp(58)
            setOnClickListener { action() }
            addView(TextView(this@DjaegerHudService).apply {
                text = icon; textSize = 18f; gravity = Gravity.CENTER; setTextColor(accent)
            })
            addView(TextView(this@DjaegerHudService).apply {
                text = label; textSize = 7f; gravity = Gravity.CENTER; setTextColor(white); maxLines = 1
                setPadding(0, dp(3), 0, 0)
            })
        }
    }
'''
if old_tool not in s:
    raise SystemExit('Build29: toolButton anchor missing')
s = s.replace(old_tool, new_tool, 1)

# Floating-app tiles become icon-forward and less card-like, matching Game Turbo's launcher strip.
old_float = '''            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; setPadding(dp(4), dp(3), dp(4), dp(3))
                background = rounded(card, Color.TRANSPARENT, 8)
            }
            item.addView(ImageView(this).apply { setImageDrawable(app.icon); scaleType = ImageView.ScaleType.FIT_CENTER }, LinearLayout.LayoutParams(dp(31), dp(31)))
'''
new_float = '''            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(dp(5), dp(5), dp(5), dp(4))
                background = rounded(Color.argb(80, 255, 255, 255), Color.TRANSPARENT, 14)
            }
            item.addView(ImageView(this).apply {
                setImageDrawable(app.icon); scaleType = ImageView.ScaleType.FIT_CENTER
            }, LinearLayout.LayoutParams(dp(34), dp(34)))
'''
if old_float not in s:
    raise SystemExit('Build29: floating tile anchor missing')
s = s.replace(old_float, new_float, 1)
s = s.replace('}, LinearLayout.LayoutParams(dp(47), -2))', '}, LinearLayout.LayoutParams(dp(52), -2))', 1)

# Section titles are quieter and spaced like toolbox group labels.
old_section = '''    private fun sectionTitle(textValue: String): TextView = TextView(this).apply {
        text = textValue; textSize = 8f; setTextColor(muted); typeface = Typeface.DEFAULT_BOLD
        setPadding(dp(3), dp(8), dp(3), dp(4))
    }
'''
new_section = '''    private fun sectionTitle(textValue: String): TextView = TextView(this).apply {
        text = textValue
        textSize = 8f
        letterSpacing = 0.08f
        setTextColor(muted)
        typeface = Typeface.DEFAULT_BOLD
        setPadding(dp(3), dp(9), dp(3), dp(4))
    }
'''
if old_section not in s:
    raise SystemExit('Build29: sectionTitle anchor missing')
s = s.replace(old_section, new_section, 1)

# Runtime telemetry updates must remain in-place. No overlay rebuild is allowed from polling.
required = [
    'private fun updateOverlayContent()',
    'private val pollRunnable: Runnable = object : Runnable',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'launchMiuiFreeform',
    '__DJAEGER_FREEFORM_CONFIRMED__',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")',
    'runDjaegerBoost()', 'toggleDnd()', 'takeScreenshot()', 'openScreenRecorder()', 'openVoiceChanger()'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build29 regression: required marker missing: {marker}')

apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body or 'rebuildOverlayKeepingPosition()' in apply_body:
    raise SystemExit('Build29 regression: anti-flicker session update invariant broken')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build29 regression: polling UI rebuild found: {forbidden_call}')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build29 regression: forbidden behavior present: {forbidden}')

h.write_text(s)
print('Build 29 MIUI interaction phase 3 applied: proportions/tiles/gesture polish, behavior preserved')
