from pathlib import Path
import re

# DJAEGER Control Center Build 22
# Goal: keep one WindowManager view attached during an ACTIVE game session.
# Polling updates bound TextViews in place; remove/add is reserved for actual HUD state transitions.

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

g = Path('app/build.gradle.kts')
s = g.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 23', s, count=1)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.10.1-rc-hud-flicker-fix"', s, count=1)
g.write_text(s)

m = pkg / 'MainActivity.kt'
s = m.read_text()
s = s.replace(
    'GAMING TURBO • v0.10.0 RC • DJAEGER AI + KERNEL SYNC • REALTIME 1s',
    'GAMING TURBO • v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC • REALTIME 1s'
)
s = s.replace('DJAEGER v0.10.0 RC', 'DJAEGER v0.10.1 RC')
m.write_text(s)

h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

# Runtime bindings: these references belong to the currently attached overlay only.
field_anchor = '    private var lastY = 155\n'
field_extra = '''    private var lastY = 155

    // Build 22: persistent HUD bindings. Never remove/re-add the overlay for telemetry refresh.
    private var compactFpsView: TextView? = null
    private var compactCpuView: TextView? = null
    private var compactModeView: TextView? = null
    private var expandedFpsView: TextView? = null
    private var expandedFrameView: TextView? = null
    private var expandedCpuView: TextView? = null
    private var expandedGpuView: TextView? = null
    private var expandedSessionView: TextView? = null
'''
if field_anchor not in s:
    raise SystemExit('Build22: field anchor not found')
s = s.replace(field_anchor, field_extra, 1)

# Single-flight polling: schedule the next poll only after this poll has completed on main.
old_poll = '''    private val pollRunnable = object : Runnable {
        override fun run() {
            thread(name = "djaeger-hud-poll") {
                val raw = runRoot(
                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +
                        "echo __DJAEGER_TELEMETRY__; " +
                        "tail -n 1 /data/adb/djaeger_ai/telemetry.csv 2>/dev/null"
                )
                val nextSnapshot = parseSnapshot(raw)
                val active = isGameSessionActive(nextSnapshot)

                mainHandler.post {
                    snapshot = nextSnapshot
                    applySessionState(active)
                }
            }
            mainHandler.postDelayed(this, if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS)
        }
    }
'''
new_poll = '''    private val pollRunnable = object : Runnable {
        override fun run() {
            thread(name = "djaeger-hud-poll") {
                val raw = runRoot(
                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +
                        "echo __DJAEGER_TELEMETRY__; " +
                        "tail -n 1 /data/adb/djaeger_ai/telemetry.csv 2>/dev/null"
                )
                val nextSnapshot = parseSnapshot(raw)
                val active = isGameSessionActive(nextSnapshot)

                mainHandler.post {
                    snapshot = nextSnapshot
                    applySessionState(active)
                    // Single-flight: no overlapping root polls and no out-of-order UI refresh.
                    mainHandler.postDelayed(
                        pollRunnable,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )
                }
            }
        }
    }
'''
if old_poll not in s:
    raise SystemExit('Build22: pollRunnable anchor not found')
s = s.replace(old_poll, new_poll, 1)

# Critical flicker fix: attached overlay is stable while ACTIVE; only its text is refreshed.
old_apply = '''        if (overlayView == null) {
            hudState = HudState.HANDLE
            showOverlay()
        } else {
            rebuildOverlayKeepingPosition()
        }
'''
new_apply = '''        if (overlayView == null) {
            hudState = HudState.HANDLE
            showOverlay()
        } else {
            updateOverlayContent()
        }
'''
if old_apply not in s:
    raise SystemExit('Build22: applySessionState anchor not found')
s = s.replace(old_apply, new_apply, 1)

# Compact HUD bindings.
old_compact = '''        row.addView(compactText("◆ DJAEGER", green))
        row.addView(compactText("${snapshot.fps} FPS"))
        row.addView(compactText("${snapshot.cpuTemp}°C"))
        row.addView(compactText(snapshot.mode))
'''
new_compact = '''        row.addView(compactText("◆ DJAEGER", green))
        compactFpsView = compactText("${snapshot.fps} FPS").also { row.addView(it) }
        compactCpuView = compactText("${snapshot.cpuTemp}°C").also { row.addView(it) }
        compactModeView = compactText(snapshot.mode).also { row.addView(it) }
'''
if old_compact not in s:
    raise SystemExit('Build22: compact HUD anchor not found')
s = s.replace(old_compact, new_compact, 1)

# Expanded metrics become bound views rather than throw-away values.
old_metrics = '''        addMetric(metrics, "FPS", snapshot.fps)
        addMetric(metrics, "FRAME", "${snapshot.frameMs} ms")
        addMetric(metrics, "CPU", "${snapshot.cpuTemp}°C")
        addMetric(metrics, "GPU", "${snapshot.gpuTemp}°C")
'''
new_metrics = '''        expandedFpsView = addMetric(metrics, "FPS", snapshot.fps)
        expandedFrameView = addMetric(metrics, "FRAME", "${snapshot.frameMs} ms")
        expandedCpuView = addMetric(metrics, "CPU", "${snapshot.cpuTemp}°C")
        expandedGpuView = addMetric(metrics, "GPU", "${snapshot.gpuTemp}°C")
'''
if old_metrics not in s:
    raise SystemExit('Build22: expanded metrics anchor not found')
s = s.replace(old_metrics, new_metrics, 1)

old_session_view = '''        box.addView(TextView(this).apply {
            text = "${snapshot.game}  •  ${snapshot.session.uppercase(Locale.US)}"
            textSize = 11f
            setTextColor(muted)
            setPadding(dp(4), dp(9), 0, dp(7))
        })
'''
new_session_view = '''        expandedSessionView = TextView(this).apply {
            text = "${snapshot.game}  •  ${snapshot.session.uppercase(Locale.US)}"
            textSize = 11f
            setTextColor(muted)
            setPadding(dp(4), dp(9), 0, dp(7))
        }.also { box.addView(it) }
'''
if old_session_view not in s:
    raise SystemExit('Build22: session view anchor not found')
s = s.replace(old_session_view, new_session_view, 1)

# Return the value TextView so it can be updated in place.
old_add_metric = '''    private fun addMetric(parent: LinearLayout, label: String, value: String) {
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
        }
        column.addView(TextView(this).apply {
            text = label
            textSize = 9f
            setTextColor(muted)
        })
        column.addView(TextView(this).apply {
            text = value
            textSize = 17f
            setTextColor(green)
            typeface = Typeface.DEFAULT_BOLD
        })
        parent.addView(column, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
    }
'''
new_add_metric = '''    private fun addMetric(parent: LinearLayout, label: String, value: String): TextView {
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
        }
        column.addView(TextView(this).apply {
            text = label
            textSize = 9f
            setTextColor(muted)
        })
        val valueView = TextView(this).apply {
            text = value
            textSize = 17f
            setTextColor(green)
            typeface = Typeface.DEFAULT_BOLD
        }
        column.addView(valueView)
        parent.addView(column, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        return valueView
    }
'''
if old_add_metric not in s:
    raise SystemExit('Build22: addMetric anchor not found')
s = s.replace(old_add_metric, new_add_metric, 1)

# Clear stale references whenever an actual state transition detaches the view.
old_remove_tail = '''        overlayView = null
        overlayParams = null
    }
'''
new_remove_tail = '''        overlayView = null
        overlayParams = null
        compactFpsView = null
        compactCpuView = null
        compactModeView = null
        expandedFpsView = null
        expandedFrameView = null
        expandedCpuView = null
        expandedGpuView = null
        expandedSessionView = null
    }
'''
if old_remove_tail not in s:
    raise SystemExit('Build22: removeOverlay tail anchor not found')
s = s.replace(old_remove_tail, new_remove_tail, 1)

# In-place UI refresh. No WindowManager removeView/addView occurs here.
insert_anchor = '    private fun buildHandle(): View {\n'
update_method = '''    private fun updateOverlayContent() {
        compactFpsView?.text = "${snapshot.fps} FPS"
        compactCpuView?.text = "${snapshot.cpuTemp}°C"
        compactModeView?.text = snapshot.mode
        expandedFpsView?.text = snapshot.fps
        expandedFrameView?.text = "${snapshot.frameMs} ms"
        expandedCpuView?.text = "${snapshot.cpuTemp}°C"
        expandedGpuView?.text = "${snapshot.gpuTemp}°C"
        expandedSessionView?.text = "${snapshot.game}  •  ${snapshot.session.uppercase(Locale.US)}"
    }

'''
if insert_anchor not in s:
    raise SystemExit('Build22: buildHandle insertion anchor not found')
s = s.replace(insert_anchor, update_method + insert_anchor, 1)

# Static invariants: polling path must never rebuild/re-attach an already visible HUD.
if 'else {\n            rebuildOverlayKeepingPosition()\n        }' in s:
    raise SystemExit('Build22: polling rebuild path still present')
if 'private fun updateOverlayContent()' not in s:
    raise SystemExit('Build22: in-place updater missing')
if 'mainHandler.postDelayed(this,' in s:
    raise SystemExit('Build22: overlapping poll scheduler still present')

h.write_text(s)
print('Build 22 persistent HUD flicker fix applied')
