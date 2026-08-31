from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

# Stage 2 changes hierarchy only. Existing actions, telemetry, session lifecycle,
# freeform bridge, polling and DJAEGER authority must remain intact.
g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 28', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.2-rc-miui-panel-phase2"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.1 RC • MIUI VISUAL PHASE 1 • REALTIME 1s',
                'GAMING TURBO • v0.11.2 RC • MIUI PANEL PHASE 2 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.1 RC', 'DJAEGER v0.11.2 RC')
m.write_text(ms)

start = s.find('    private fun buildPanel(extended: Boolean): View {')
end = s.find('\n    private fun buildToolGrid(): View {', start)
if start < 0 or end < 0:
    raise SystemExit('Build28: buildPanel boundaries missing')

new_panel = r'''    private fun buildPanel(extended: Boolean): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(panel, Color.argb(92, 124, 192, 224), 22)
            setPadding(dp(14), dp(11), dp(14), dp(13))
            minimumWidth = dp(318)
        }

        // MIUI-like top bar: identity left, panel controls right.
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(TextView(this).apply {
            text = "DJAEGER  GAME TURBO"
            textSize = 12f
            letterSpacing = 0.04f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(iconButton(if (extended) "↙" else "↗") {
            hudState = if (extended) HudState.PANEL else HudState.EXTENDED
            rebuildOverlayKeepingPosition()
        })
        header.addView(iconButton("⚙") { openControlCenter() })
        box.addView(header)

        // Status/telemetry strip sits directly under the title like Game Turbo.
        val status = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(Color.argb(96, 255, 255, 255), Color.TRANSPARENT, 15)
            setPadding(dp(9), dp(7), dp(9), dp(7))
        }
        panelMode = TextView(this).apply {
            text = snapshot.mode
            textSize = 9f
            setTextColor(accent)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER_VERTICAL
        }
        panelFps = metricText("FPS ${snapshot.fps}")
        panelCpu = metricText("CPU ${snapshot.cpuTemp}°")
        panelGpu = metricText("GPU ${snapshot.gpuTemp}°")
        status.addView(panelMode, LinearLayout.LayoutParams(0, -2, 0.85f))
        status.addView(panelFps, LinearLayout.LayoutParams(0, -2, 1f))
        status.addView(panelCpu, LinearLayout.LayoutParams(0, -2, 1f))
        status.addView(panelGpu, LinearLayout.LayoutParams(0, -2, 1f))
        box.addView(status, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(8) })

        // Primary Game Turbo toolbox remains backed by the existing real actions.
        box.addView(sectionTitle("GAME TOOLS"))
        box.addView(buildToolGrid())

        // Floating launcher is promoted into the main panel instead of being hidden.
        val floatingHeader = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(3), dp(8), dp(3), dp(4))
        }
        floatingHeader.addView(TextView(this).apply {
            text = "FLOATING APPS"
            textSize = 8f
            letterSpacing = 0.08f
            setTextColor(muted)
            typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, -2, 1f))
        floatingHeader.addView(TextView(this).apply {
            text = if (extended) "LESS" else "MORE  ›"
            textSize = 8f
            setTextColor(accent)
            setOnClickListener {
                hudState = if (extended) HudState.PANEL else HudState.EXTENDED
                rebuildOverlayKeepingPosition()
            }
        })
        box.addView(floatingHeader)
        box.addView(buildFloatingApps(compact = !extended))

        if (extended) {
            box.addView(sectionTitle("PERFORMANCE MODE"))
            box.addView(buildModeRow())
        }

        panelSession = TextView(this).apply {
            text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"
            textSize = 8f
            setTextColor(muted)
            gravity = Gravity.CENTER
            setPadding(dp(3), dp(8), dp(3), dp(2))
        }
        box.addView(panelSession)

        box.addView(TextView(this).apply {
            text = "‹  sembunyikan"
            textSize = 9f
            gravity = Gravity.CENTER
            setTextColor(muted)
            setPadding(dp(4), dp(7), dp(4), dp(2))
            setOnClickListener { hudState = HudState.HANDLE; rebuildOverlayKeepingPosition() }
        })
        return box
    }
'''
s = s[:start] + new_panel + s[end:]

# Make the tool area a single horizontal MIUI-like strip. Existing actions are unchanged.
tool_start = s.find('    private fun buildToolGrid(): View {')
tool_end = s.find('\n    private fun buildModeRow(): View {', tool_start)
if tool_start < 0 or tool_end < 0:
    raise SystemExit('Build28: buildToolGrid boundaries missing')
new_tools = r'''    private fun buildToolGrid(): View {
        val scroll = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(3), 0, dp(3))
        }
        val items = listOf(
            Triple("♟", "Boost", { runDjaegerBoost() }),
            Triple("☾", "DND", { toggleDnd() }),
            Triple("✂", "Screenshot", { takeScreenshot() }),
            Triple("▣", "Record", { openScreenRecorder() }),
            Triple("♩", "Voice", { openVoiceChanger() }),
            Triple("⚙", "Settings", { openControlCenter() })
        )
        items.forEach { (icon, label, action) ->
            row.addView(toolButton(icon, label) { action() }, LinearLayout.LayoutParams(dp(72), -2).apply {
                marginStart = dp(2); marginEnd = dp(2)
            })
        }
        scroll.addView(row)
        return scroll
    }
'''
s = s[:tool_start] + new_tools + s[tool_end:]

# Restore all five owner-facing modes in the Game Turbo strip.
mode_start = s.find('    private fun buildModeRow(): View {')
mode_end = s.find('\n    private fun buildFloatingApps(', mode_start)
if mode_start < 0 or mode_end < 0:
    raise SystemExit('Build28: buildModeRow boundaries missing')
new_modes = r'''    private fun buildModeRow(): View {
        val scroll = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS").forEach { mode ->
            row.addView(TextView(this).apply {
                text = mode
                textSize = 8f
                gravity = Gravity.CENTER
                setTextColor(if (snapshot.mode == mode) white else muted)
                background = rounded(
                    if (snapshot.mode == mode) Color.argb(90, 45, 190, 255) else card,
                    if (snapshot.mode == mode) accent else Color.TRANSPARENT,
                    14
                )
                setPadding(dp(10), dp(7), dp(10), dp(7))
                setOnClickListener { setTrustedMode(mode) }
            }, LinearLayout.LayoutParams(dp(66), -2).apply { marginStart = dp(2); marginEnd = dp(2) })
        }
        scroll.addView(row)
        return scroll
    }
'''
s = s[:mode_start] + new_modes + s[mode_end:]

required = [
    'private fun updateOverlayContent()',
    'private val pollRunnable: Runnable = object : Runnable',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'launchMiuiFreeform',
    '__DJAEGER_FREEFORM_CONFIRMED__',
    'djaeger-ai mode',
    'runDjaegerBoost()', 'toggleDnd()', 'takeScreenshot()',
    'openScreenRecorder()', 'openVoiceChanger()', 'openControlCenter()',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build28 regression: required marker missing: {marker}')

apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body or 'rebuildOverlayKeepingPosition()' in apply_body:
    raise SystemExit('Build28 regression: polling flicker invariant broken')

for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build28 regression: forbidden behavior present: {forbidden}')

h.write_text(s)
print('Build 28 MIUI panel phase 2 applied: hierarchy/tool strip/floating apps/five modes')
