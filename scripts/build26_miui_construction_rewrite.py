from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

g = Path('app/build.gradle.kts')
s = g.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 26', s, count=1)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.0-rc-miui-construction"', s, count=1)
g.write_text(s)

m = pkg / 'MainActivity.kt'
s = m.read_text()
s = re.sub(r'GAMING TURBO • v0\.10\.2 RC • REALTIME TELEMETRY \+ MULTI WINDOW • 1s',
           'GAMING TURBO • v0.11.0 RC • MIUI CONSTRUCTION • REALTIME 1s', s)
s = s.replace('DJAEGER v0.10.2 RC', 'DJAEGER v0.11.0 RC')
m.write_text(s)

(pkg / 'DjaegerHudService.kt').write_text(r'''package com.djaeger.controlcenter

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Locale
import kotlin.concurrent.thread
import kotlin.math.abs

/**
 * DJAEGER Game Turbo overlay.
 *
 * Construction follows the behavior mapped from the user's MIUI SecurityCenter
 * Game Booster + Joyose pair, while keeping DJAEGER as the authority backend.
 * MIUI-specific launch behavior is requested through root/ActivityManager and
 * then verified from ActivityTaskManager state instead of faking a floating UI.
 */
class DjaegerHudService : Service() {
    companion object {
        private const val CHANNEL_ID = "djaeger_game_turbo"
        private const val NOTIFICATION_ID = 12928
        private const val ACTIVE_POLL_MS = 1000L
        private const val IDLE_POLL_MS = 1800L
        private const val MAX_FLOATING_APPS = 12
    }

    private enum class HudState { HANDLE, PANEL, EXTENDED }

    private data class RuntimeSnapshot(
        val fps: String = "--",
        val frameMs: String = "--",
        val cpuTemp: String = "--",
        val gpuTemp: String = "--",
        val mode: String = "AUTO",
        val game: String = "NA",
        val window: String = "INACTIVE",
        val session: String = "INACTIVE"
    )

    private data class LaunchableApp(
        val label: String,
        val packageName: String,
        val activityName: String,
        val icon: Drawable
    )

    private val mainHandler = Handler(Looper.getMainLooper())
    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private var overlayParams: WindowManager.LayoutParams? = null
    private var hudState = HudState.HANDLE
    private var gameSessionActive = false
    private var suppressedForCurrentSession = false
    private var snapshot = RuntimeSnapshot()
    private var lastX = 0
    private var lastY = 145
    private var handleOnRight = false
    private var toolsExpanded = false
    private var floatingExpanded = true

    // Views updated in-place by the 1 s poll. Polling never rebuilds the window.
    private var panelFps: TextView? = null
    private var panelCpu: TextView? = null
    private var panelGpu: TextView? = null
    private var panelMode: TextView? = null
    private var panelSession: TextView? = null

    private val accent = Color.rgb(20, 173, 255)
    private val accentSoft = Color.rgb(41, 126, 190)
    private val dark = Color.argb(244, 5, 13, 22)
    private val panel = Color.argb(250, 8, 18, 30)
    private val card = Color.argb(247, 13, 27, 42)
    private val muted = Color.rgb(157, 181, 204)
    private val white = Color.rgb(240, 246, 252)
    private val green = Color.rgb(69, 221, 141)

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        mainHandler.post(pollRunnable)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        mainHandler.removeCallbacksAndMessages(null)
        removeOverlay()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "DJAEGER Game Turbo", NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification = Notification.Builder(this, CHANNEL_ID)
        .setContentTitle("DJAEGER AI Game Turbo")
        .setContentText("MIUI-style in-game control aktif")
        .setSmallIcon(R.drawable.ic_djaeger_gaming_turbo)
        .setOngoing(true)
        .build()

    private val pollRunnable: Runnable = object : Runnable {
        override fun run() {
            thread(name = "djaeger-hud-poll") {
                val raw = runRoot(
                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +
                        "echo __DJAEGER_THERMAL__; " +
                        "for z in /sys/class/thermal/thermal_zone*; do " +
                        "[ -r \\\"${'$'}z/type\\\" ] || continue; [ -r \\\"${'$'}z/temp\\\" ] || continue; " +
                        "read -r n < \\\"${'$'}z/type\\\"; case \\\"${'$'}n\\\" in " +
                        "cpu-*-usr|cpuss-*-usr|gpuss-*-usr) read -r t < \\\"${'$'}z/temp\\\"; " +
                        "printf '%s=%s\\\\n' \\\"${'$'}n\\\" \\\"${'$'}t\\\";; esac; done; " +
                        "echo __DJAEGER_LATENCY__; " +
                        "L=\\\"${'$'}(cat /data/adb/djaeger_ai/frame_layer 2>/dev/null)\\\"; " +
                        "[ -n \\\"${'$'}L\\\" ] && dumpsys SurfaceFlinger --latency \\\"${'$'}L\\\" 2>/dev/null; " +
                        "echo __DJAEGER_CSV__; " +
                        "tail -n 1 /data/adb/modules/djaeger_game_stabilizer/telemetry.csv 2>/dev/null"
                )
                val next = parseSnapshot(raw)
                val active = isGameSessionActive(next)
                mainHandler.post {
                    snapshot = next
                    applySessionState(active)
                    mainHandler.postDelayed(
                        this,
                        if (gameSessionActive) ACTIVE_POLL_MS else IDLE_POLL_MS
                    )
                }
            }
        }
    }

    private fun applySessionState(active: Boolean) {
        if (!active) {
            suppressedForCurrentSession = false
            if (gameSessionActive) {
                gameSessionActive = false
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

    private fun isGameSessionActive(state: RuntimeSnapshot): Boolean {
        val window = state.window.uppercase(Locale.US)
        val session = state.session.uppercase(Locale.US)
        val game = state.game.uppercase(Locale.US)
        if (window == "ACTIVE" || session == "ACTIVE") return true
        if (game == "NA" || game == "INACTIVE" || game.isBlank()) return false
        return window != "INACTIVE"
    }

    private fun parseSnapshot(raw: String): RuntimeSnapshot {
        val runtimeText = raw.substringBefore("__DJAEGER_THERMAL__")
        val thermalText = raw.substringAfter("__DJAEGER_THERMAL__", "").substringBefore("__DJAEGER_LATENCY__")
        val latencyText = raw.substringAfter("__DJAEGER_LATENCY__", "").substringBefore("__DJAEGER_CSV__")
        val csvText = raw.substringAfter("__DJAEGER_CSV__", "").trim()

        val runtime = runtimeText.lineSequence().mapNotNull { line ->
            val split = line.indexOf('=')
            if (split <= 0) null else {
                val key = line.substring(0, split).trim().lowercase(Locale.US)
                val value = line.substring(split + 1).trim().trim('"', '\'')
                key to value
            }
        }.toMap()

        fun thermalC(value: String?): Double? {
            val n = value?.trim()?.toDoubleOrNull() ?: return null
            return if (abs(n) > 1000.0) n / 1000.0 else n
        }
        var cpuNow: Double? = null
        var gpuNow: Double? = null
        thermalText.lineSequence().forEach { line ->
            val split = line.indexOf('=')
            if (split <= 0) return@forEach
            val type = line.substring(0, split).trim()
            val temp = thermalC(line.substring(split + 1)) ?: return@forEach
            if (type.startsWith("gpuss-")) gpuNow = maxOf(gpuNow ?: temp, temp)
            if (type.startsWith("cpu-") || type.startsWith("cpuss-")) cpuNow = maxOf(cpuNow ?: temp, temp)
        }

        val present = latencyText.lineSequence().drop(1).mapNotNull { line ->
            val cols = line.trim().split(Regex("\\s+"))
            cols.getOrNull(1)?.toLongOrNull()?.takeIf { it > 0L }
        }.toList()
        val intervals = present.zipWithNext { a, b -> (b - a) / 1_000_000.0 }
            .filter { it in 4.0..250.0 }
            .takeLast(30)
        val liveFrame = intervals.takeIf { it.size >= 3 }?.average()
        val liveFps = liveFrame?.takeIf { it > 0.0 }?.let { 1000.0 / it }

        val csv = csvText.split(',')
        fun csvNumber(index: Int): Double? = csv.getOrNull(index)?.trim()?.toDoubleOrNull()
        val fps = liveFps ?: csvNumber(10)
        val frame = liveFrame ?: csvNumber(9)
        val cpu = cpuNow ?: csvNumber(1)
        val gpu = gpuNow ?: csvNumber(2)
        fun one(v: Double?): String = v?.takeIf { it.isFinite() }?.let { String.format(Locale.US, "%.1f", it) } ?: "--"
        fun temp(v: Double?): String = v?.takeIf { it.isFinite() }?.let { String.format(Locale.US, "%.0f", it) } ?: "--"

        val game = runtime["game"] ?: runtime["game_id"] ?: runtime["package"] ?: "NA"
        val mode = runtime["user_mode"] ?: runtime["mode"] ?: "AUTO"
        val window = runtime["window_mode"] ?: runtime["window"] ?: runtime["window_state"] ?: "INACTIVE"
        val active = runtime["active"]?.lowercase(Locale.US) in setOf("1", "true", "active")
        val session = runtime["session"] ?: runtime["session_state"]
            ?: if (active || window.equals("ACTIVE", true)) "ACTIVE" else "INACTIVE"
        return RuntimeSnapshot(one(fps), one(frame), temp(cpu), temp(gpu), mode.uppercase(Locale.US), game, window, session)
    }

    private fun showOverlay() {
        removeOverlay(rememberPosition = false)
        val view = when (hudState) {
            HudState.HANDLE -> buildHandle()
            HudState.PANEL -> buildPanel(false)
            HudState.EXTENDED -> buildPanel(true)
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or if (handleOnRight) Gravity.END else Gravity.START
            x = dp(lastX)
            y = dp(lastY)
        }
        attachPanelDrag(view, params)
        overlayView = view
        overlayParams = params
        windowManager.addView(view, params)
    }

    private fun rebuildOverlayKeepingPosition() {
        overlayParams?.let { p -> lastX = pxToDp(p.x); lastY = pxToDp(p.y) }
        showOverlay()
    }

    private fun removeOverlay(rememberPosition: Boolean = true) {
        if (rememberPosition) overlayParams?.let { p -> lastX = pxToDp(p.x); lastY = pxToDp(p.y) }
        overlayView?.let { try { windowManager.removeView(it) } catch (_: Exception) {} }
        overlayView = null
        overlayParams = null
        panelFps = null; panelCpu = null; panelGpu = null; panelMode = null; panelSession = null
    }

    private fun updateOverlayContent() {
        panelFps?.text = "FPS ${snapshot.fps}"
        panelCpu?.text = "CPU ${snapshot.cpuTemp}°"
        panelGpu?.text = "GPU ${snapshot.gpuTemp}°"
        panelMode?.text = snapshot.mode
        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"
    }

    private fun buildHandle(): View {
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

    private fun attachHandleGesture(view: View) {
        var downX = 0f; var downY = 0f; var moved = false
        view.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> { downX = event.rawX; downY = event.rawY; moved = false; true }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - downX; val dy = event.rawY - downY
                    if (abs(dx) > dp(20) || abs(dy) > dp(20)) moved = true
                    if (abs(dx) > dp(34) && abs(dx) > abs(dy)) {
                        hudState = HudState.PANEL
                        rebuildOverlayKeepingPosition()
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (!moved) { hudState = HudState.PANEL; rebuildOverlayKeepingPosition() }
                    true
                }
                else -> true
            }
        }
    }

    private fun attachPanelDrag(view: View, params: WindowManager.LayoutParams) {
        var downX = 0f; var downY = 0f; var startX = 0; var startY = 0; var dragging = false
        view.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> { downX = event.rawX; downY = event.rawY; startX = params.x; startY = params.y; dragging = false; false }
                MotionEvent.ACTION_MOVE -> {
                    if (abs(event.rawX - downX) + abs(event.rawY - downY) > dp(16)) dragging = true
                    if (dragging) {
                        val dx = (event.rawX - downX).toInt(); val dy = (event.rawY - downY).toInt()
                        params.x = if (handleOnRight) (startX - dx).coerceAtLeast(0) else (startX + dx).coerceAtLeast(0)
                        params.y = (startY + dy).coerceAtLeast(0)
                        try { windowManager.updateViewLayout(view, params) } catch (_: Exception) {}
                        true
                    } else false
                }
                else -> false
            }
        }
    }

    private fun buildPanel(extended: Boolean): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(panel, accentSoft, 16)
            setPadding(dp(11), dp(9), dp(11), dp(11))
        }

        val header = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        header.addView(TextView(this).apply {
            text = "ᛉ  DJAEGER AI\n     GAME TURBO"
            textSize = 11f; setTextColor(white); typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        header.addView(iconButton(if (extended) "↙" else "↗") {
            hudState = if (extended) HudState.PANEL else HudState.EXTENDED
            rebuildOverlayKeepingPosition()
        })
        header.addView(iconButton("⚙") { openControlCenter() })
        box.addView(header)

        val profile = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            background = rounded(card, Color.TRANSPARENT, 9); setPadding(dp(8), dp(6), dp(8), dp(6))
        }
        profile.addView(TextView(this).apply { text = "Performance"; textSize = 10f; setTextColor(accent) }, LinearLayout.LayoutParams(0, -2, 1f))
        panelMode = TextView(this).apply { text = snapshot.mode; textSize = 10f; setTextColor(accent); setPadding(dp(8), 0, 0, 0) }
        profile.addView(panelMode)
        box.addView(profile, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(7) })

        val metrics = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(3), dp(7), dp(3), dp(6)) }
        panelCpu = metricText("CPU ${snapshot.cpuTemp}°")
        panelGpu = metricText("GPU ${snapshot.gpuTemp}°")
        panelFps = metricText("FPS ${snapshot.fps}")
        metrics.addView(panelCpu, LinearLayout.LayoutParams(0, -2, 1f))
        metrics.addView(panelGpu, LinearLayout.LayoutParams(0, -2, 1f))
        metrics.addView(panelFps, LinearLayout.LayoutParams(0, -2, 1f))
        box.addView(metrics)

        val divider = View(this).apply { setBackgroundColor(accentSoft) }
        box.addView(divider, LinearLayout.LayoutParams(-1, dp(1)))

        box.addView(buildToolGrid())
        panelSession = TextView(this).apply {
            text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"
            textSize = 8f; setTextColor(muted); gravity = Gravity.CENTER_VERTICAL; setPadding(dp(3), dp(5), 0, 0)
        }
        box.addView(panelSession)

        if (extended) {
            box.addView(sectionTitle("PERFORMANCE MODE"))
            box.addView(buildModeRow())
            box.addView(sectionTitle("FLOATING APPS"))
            box.addView(buildFloatingApps())
        } else {
            val floatingTitle = sectionTitle("Floating apps  ›").apply {
                setOnClickListener { hudState = HudState.EXTENDED; rebuildOverlayKeepingPosition() }
            }
            box.addView(floatingTitle)
            box.addView(buildFloatingApps(compact = true))
        }

        box.addView(TextView(this).apply {
            text = "‹  sembunyikan"
            textSize = 9f; gravity = Gravity.CENTER; setTextColor(muted); setPadding(dp(4), dp(7), dp(4), dp(2))
            setOnClickListener { hudState = HudState.HANDLE; rebuildOverlayKeepingPosition() }
        })
        return box
    }

    private fun buildToolGrid(): View {
        val outer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, dp(7), 0, 0) }
        val first = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val second = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        first.addView(toolButton("♟", "Boost") { runDjaegerBoost() }, LinearLayout.LayoutParams(0, -2, 1f))
        first.addView(toolButton("☾", "DND") { toggleDnd() }, LinearLayout.LayoutParams(0, -2, 1f))
        first.addView(toolButton("✂", "Screenshot") { takeScreenshot() }, LinearLayout.LayoutParams(0, -2, 1f))
        second.addView(toolButton("▣", "Record") { openScreenRecorder() }, LinearLayout.LayoutParams(0, -2, 1f))
        second.addView(toolButton("♩", "Voice") { openVoiceChanger() }, LinearLayout.LayoutParams(0, -2, 1f))
        second.addView(toolButton("⚙", "Settings") { openControlCenter() }, LinearLayout.LayoutParams(0, -2, 1f))
        outer.addView(first); outer.addView(second)
        return outer
    }

    private fun buildModeRow(): View {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf("DINGIN", "SEDANG", "PANAS").forEach { mode ->
            row.addView(TextView(this).apply {
                text = mode; textSize = 8f; gravity = Gravity.CENTER; setTextColor(if (snapshot.mode == mode) accent else muted)
                background = rounded(card, if (snapshot.mode == mode) accent else Color.TRANSPARENT, 8)
                setPadding(dp(5), dp(7), dp(5), dp(7)); setOnClickListener { setTrustedMode(mode) }
            }, LinearLayout.LayoutParams(0, -2, 1f).apply { marginStart = dp(2); marginEnd = dp(2) })
        }
        return row
    }

    private fun buildFloatingApps(compact: Boolean = false): View {
        val apps = queryLaunchableApps().take(if (compact) 6 else MAX_FLOATING_APPS)
        val scroll = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        apps.forEach { app ->
            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; setPadding(dp(4), dp(3), dp(4), dp(3))
                background = rounded(card, Color.TRANSPARENT, 8)
            }
            item.addView(ImageView(this).apply { setImageDrawable(app.icon); scaleType = ImageView.ScaleType.FIT_CENTER }, LinearLayout.LayoutParams(dp(31), dp(31)))
            item.addView(TextView(this).apply {
                text = if (app.label.length > 8) app.label.take(7) + "…" else app.label
                textSize = 7f; gravity = Gravity.CENTER; setTextColor(white); maxLines = 1
            }, LinearLayout.LayoutParams(dp(47), -2))
            item.setOnClickListener { launchMiuiFreeform(app) }
            row.addView(item)
        }
        row.addView(TextView(this).apply {
            text = "+"; textSize = 20f; gravity = Gravity.CENTER; setTextColor(accent)
            background = rounded(card, accentSoft, 8); setPadding(dp(11), dp(9), dp(11), dp(9))
            setOnClickListener { hudState = HudState.EXTENDED; rebuildOverlayKeepingPosition() }
        })
        scroll.addView(row)
        return scroll
    }

    private fun queryLaunchableApps(): List<LaunchableApp> {
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return packageManager.queryIntentActivities(intent, 0)
            .filter { it.activityInfo.packageName != packageName }
            .distinctBy { it.activityInfo.packageName }
            .map { LaunchableApp(it.loadLabel(packageManager).toString(), it.activityInfo.packageName, it.activityInfo.name, it.loadIcon(packageManager)) }
            .sortedBy { it.label.lowercase(Locale.US) }
    }

    /**
     * MIUI-native construction request:
     * 1) request freeform windowing mode 5 from ActivityManager,
     * 2) verify task/window state after launch,
     * 3) retry through cmd activity if the first launcher path was rejected.
     * Once the task is genuinely in MIUI freeform, MIUI owns drag, mini/pin,
     * restore, maximize and close transitions exactly like Game Turbo.
     */
    private fun launchMiuiFreeform(app: LaunchableApp) {
        val pkg = app.packageName.replace(Regex("[^A-Za-z0-9._]"), "")
        val activity = app.activityName.replace(Regex("[^A-Za-z0-9._$]"), "")
        if (pkg.isBlank() || activity.isBlank()) return
        toast("Membuka ${app.label} sebagai floating window…")
        thread(name = "djaeger-miui-freeform") {
            val component = "$pkg/$activity"
            val command =
                "am start --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1; " +
                "sleep 1; " +
                "STATE=\\\"${'$'}(dumpsys activity activities 2>/dev/null | grep -A 28 -B 4 '$pkg' | tail -n 80)\\\"; " +
                "printf '%s\\\\n' \\\"${'$'}STATE\\\"; " +
                "printf '%s\\\\n' \\\"${'$'}STATE\\\" | grep -Eqi 'windowingMode=5|mWindowingMode=5|freeform' && echo __DJAEGER_FREEFORM_CONFIRMED__ || echo __DJAEGER_FREEFORM_UNCONFIRMED__"
            var result = runRoot(command)
            if (!result.contains("__DJAEGER_FREEFORM_CONFIRMED__")) {
                result += runRoot(
                    "cmd activity start-activity --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1; " +
                        "sleep 1; dumpsys activity activities 2>/dev/null | grep -A 28 -B 4 '$pkg' | tail -n 80"
                )
            }
            val confirmed = Regex("windowingMode=5|mWindowingMode=5|freeform", RegexOption.IGNORE_CASE).containsMatchIn(result)
            mainHandler.post {
                toast(if (confirmed) "${app.label} • MIUI FREEFORM" else "${app.label} dibuka; MIUI tidak mengonfirmasi freeform")
                if (confirmed) { hudState = HudState.HANDLE; rebuildOverlayKeepingPosition() }
            }
        }
    }

    private fun runDjaegerBoost() {
        thread(name = "djaeger-boost") {
            runRoot("djaeger-ai mode panas >/dev/null 2>&1")
            mainHandler.post { toast("DJAEGER performance authority aktif") }
        }
    }

    private fun toggleDnd() {
        thread(name = "djaeger-dnd") {
            val out = runRoot("cmd notification get_dnd 2>/dev/null")
            val enable = !out.contains("priority", true) && !out.contains("alarms", true) && !out.contains("none", true)
            runRoot("cmd notification set_dnd ${if (enable) "priority" else "off"} 2>/dev/null")
            mainHandler.post { toast(if (enable) "DND aktif" else "DND nonaktif") }
        }
    }

    private fun takeScreenshot() {
        thread(name = "djaeger-shot") {
            val out = runRoot("am broadcast -a miui.intent.TAKE_SCREENSHOT 2>&1")
            mainHandler.post { toast(if (out.contains("Broadcast completed", true)) "Screenshot" else "Perintah screenshot dikirim") }
        }
    }

    private fun openScreenRecorder() {
        thread(name = "djaeger-record") {
            runRoot("monkey -p com.miui.screenrecorder -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1")
            mainHandler.post { toast("Screen Recorder") }
        }
    }

    private fun openVoiceChanger() {
        thread(name = "djaeger-voice") {
            val out = runRoot("am start --user 0 -a com.miui.gamebooster.action.ACCESS_MAINACTIVITY -p com.miui.securitycenter 2>&1")
            mainHandler.post { toast(if (out.contains("Error", true)) "Voice changer membutuhkan Game Turbo MIUI" else "Game Turbo voice tools") }
        }
    }

    private fun openControlCenter() {
        val launch = packageManager.getLaunchIntentForPackage(packageName) ?: return
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(launch)
    }

    private fun setTrustedMode(mode: String) {
        val arg = when (mode) {
            "AUTO" -> "auto"; "DINGIN" -> "dingin"; "SEDANG" -> "sedang"; "HANGAT" -> "hangat"; "PANAS" -> "panas"; else -> return
        }
        thread(name = "djaeger-mode") { runRoot("djaeger-ai mode $arg") }
    }

    private fun toolButton(icon: String, label: String, action: () -> Unit): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; background = rounded(card, Color.TRANSPARENT, 8)
            setPadding(dp(4), dp(6), dp(4), dp(6)); setOnClickListener { action() }
            addView(TextView(this@DjaegerHudService).apply { text = icon; textSize = 15f; gravity = Gravity.CENTER; setTextColor(accent) })
            addView(TextView(this@DjaegerHudService).apply { text = label; textSize = 7f; gravity = Gravity.CENTER; setTextColor(white) })
        }
    }

    private fun metricText(textValue: String): TextView = TextView(this).apply {
        text = textValue; textSize = 9f; gravity = Gravity.CENTER; setTextColor(white)
    }

    private fun sectionTitle(value: String): TextView = TextView(this).apply {
        text = value; textSize = 8f; setTextColor(accent); typeface = Typeface.DEFAULT_BOLD; setPadding(dp(3), dp(8), dp(3), dp(5))
    }

    private fun iconButton(value: String, action: () -> Unit): TextView = TextView(this).apply {
        text = value; textSize = 16f; gravity = Gravity.CENTER; setTextColor(white); setPadding(dp(8), dp(3), dp(8), dp(3)); setOnClickListener { action() }
    }

    private fun shortGame(value: String): String {
        if (value.length <= 24) return value
        return value.takeLast(24)
    }

    private fun toast(value: String) = Toast.makeText(this, value, Toast.LENGTH_SHORT).show()

    private fun rounded(fill: Int, stroke: Int, radiusDp: Int): GradientDrawable = GradientDrawable().apply {
        setColor(fill); cornerRadius = dp(radiusDp).toFloat(); if (stroke != Color.TRANSPARENT) setStroke(dp(1), stroke)
    }

    private fun runRoot(command: String): String = try {
        val process = ProcessBuilder("su", "-c", command).redirectErrorStream(true).start()
        val output = BufferedReader(InputStreamReader(process.inputStream)).use { it.readText() }
        process.waitFor(); output
    } catch (_: Exception) { "" }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()
    private fun pxToDp(v: Int): Int = (v / resources.displayMetrics.density).toInt()
}
''')

# Keep package visibility narrow: launcher apps only; no QUERY_ALL_PACKAGES.
manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text()
if '<queries>' not in ms:
    pos = ms.find('<application')
    if pos < 0:
        raise SystemExit('Build26: manifest application anchor missing')
    queries = '''    <queries>\n        <intent>\n            <action android:name="android.intent.action.MAIN" />\n            <category android:name="android.intent.category.LAUNCHER" />\n        </intent>\n    </queries>\n\n'''
    ms = ms[:pos] + queries + ms[pos:]
manifest.write_text(ms)

# Build-time invariants.
h = (pkg / 'DjaegerHudService.kt').read_text()
required = [
    'private enum class HudState { HANDLE, PANEL, EXTENDED }',
    'attachHandleGesture',
    'buildFloatingApps',
    'launchMiuiFreeform',
    'windowingMode=5',
    'cmd activity start-activity --user 0 --windowingMode 5',
    'dumpsys activity activities',
    '__DJAEGER_FREEFORM_CONFIRMED__',
    'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'private fun updateOverlayContent()',
    'djaeger-ai mode',
]
for marker in required:
    if marker not in h:
        raise SystemExit(f'Build26 missing invariant: {marker}')
apply_body = h.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'rebuildOverlayKeepingPosition()' in apply_body:
    raise SystemExit('Build26: polling path must not rebuild overlay')
if 'updateOverlayContent()' not in apply_body:
    raise SystemExit('Build26: polling path must update attached views')
if 'settings put' in h or 'setprop' in h or 'iptables' in h or 'nft ' in h:
    raise SystemExit('Build26: forbidden unrelated system mutation detected')
print('Build 26 MIUI construction rewrite applied')
