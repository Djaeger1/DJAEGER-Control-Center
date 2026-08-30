from pathlib import Path

g = Path('app/build.gradle.kts')
s = g.read_text()
s = s.replace('versionCode = 19', 'versionCode = 20')
s = s.replace('versionName = "0.8.2-rc-game-turbo-compile-fix"', 'versionName = "0.8.3-rc-game-turbo-service-rewrite"')
g.write_text(s)

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

(pkg / 'DjaegerHudService.kt').write_text(r'''package com.djaeger.controlcenter

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
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
import android.widget.LinearLayout
import android.widget.TextView
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Locale
import kotlin.concurrent.thread

class DjaegerHudService : Service() {
    companion object {
        private const val CHANNEL_ID = "djaeger_game_turbo"
        private const val NOTIFICATION_ID = 12928
        private const val ACTIVE_POLL_MS = 1000L
        private const val IDLE_POLL_MS = 1800L
    }

    private enum class HudState { HANDLE, COMPACT, EXPANDED }

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

    private val mainHandler = Handler(Looper.getMainLooper())
    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private var overlayParams: WindowManager.LayoutParams? = null
    private var hudState = HudState.HANDLE
    private var gameSessionActive = false
    private var suppressedForCurrentSession = false
    private var snapshot = RuntimeSnapshot()
    private var manualScale = 1.0f
    private var lastX = 8
    private var lastY = 155

    private val green = Color.rgb(67, 227, 138)
    private val dark = Color.argb(240, 8, 12, 17)
    private val panel = Color.argb(247, 13, 18, 25)
    private val muted = Color.rgb(175, 184, 199)

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
                CHANNEL_ID,
                "DJAEGER Game Turbo",
                NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("DJAEGER Game Turbo")
            .setContentText("Auto game detection aktif")
            .setSmallIcon(R.drawable.ic_djaeger_gaming_turbo)
            .setOngoing(true)
            .build()
    }

    private val pollRunnable = object : Runnable {
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
            rebuildOverlayKeepingPosition()
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
        val runtimeText = raw.substringBefore("__DJAEGER_TELEMETRY__")
        val telemetryText = raw.substringAfter("__DJAEGER_TELEMETRY__", "")
        val runtime = runtimeText.lineSequence().mapNotNull { line ->
            val split = line.indexOf('=')
            if (split <= 0) null
            else line.substring(0, split).trim().lowercase(Locale.US) to line.substring(split + 1).trim()
        }.toMap()

        val fields = telemetryText.trim().lineSequence().lastOrNull().orEmpty().split(',')
        fun number(index: Int): Double? = fields.getOrNull(index)?.trim()?.toDoubleOrNull()
        fun temperature(index: Int): String {
            val rawValue = number(index) ?: return "--"
            val celsius = if (rawValue > 1000.0) rawValue / 1000.0 else rawValue
            return String.format(Locale.US, "%.0f", celsius)
        }

        val fps = number(9)?.let { String.format(Locale.US, "%.1f", it) } ?: "--"
        val frame = (number(10) ?: number(18))?.let { String.format(Locale.US, "%.1f", it) } ?: "--"
        val game = runtime["game"] ?: runtime["game_id"] ?: runtime["package"] ?: "NA"
        val mode = runtime["user_mode"] ?: runtime["mode"] ?: "AUTO"
        val window = runtime["window"] ?: runtime["window_state"] ?: "INACTIVE"
        val session = runtime["session"] ?: runtime["session_state"] ?: if (window.equals("ACTIVE", true)) "ACTIVE" else "INACTIVE"

        return RuntimeSnapshot(
            fps = fps,
            frameMs = frame,
            cpuTemp = temperature(1),
            gpuTemp = temperature(2),
            mode = mode.uppercase(Locale.US),
            game = game,
            window = window,
            session = session
        )
    }

    private fun showOverlay() {
        removeOverlay(rememberPosition = false)
        val view = when (hudState) {
            HudState.HANDLE -> buildHandle()
            HudState.COMPACT -> buildCompactHud()
            HudState.EXPANDED -> buildExpandedHud()
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = dp(lastX)
            y = dp(lastY)
        }

        view.scaleX = manualScale
        view.scaleY = manualScale
        attachDrag(view, params)
        overlayView = view
        overlayParams = params
        windowManager.addView(view, params)
    }

    private fun rebuildOverlayKeepingPosition() {
        overlayParams?.let { params ->
            lastX = pxToDp(params.x)
            lastY = pxToDp(params.y)
        }
        showOverlay()
    }

    private fun removeOverlay(rememberPosition: Boolean = true) {
        if (rememberPosition) {
            overlayParams?.let { params ->
                lastX = pxToDp(params.x)
                lastY = pxToDp(params.y)
            }
        }
        overlayView?.let { view ->
            try { windowManager.removeView(view) } catch (_: Exception) { }
        }
        overlayView = null
        overlayParams = null
    }

    private fun attachDrag(view: View, params: WindowManager.LayoutParams) {
        var downX = 0f
        var downY = 0f
        var startX = 0
        var startY = 0
        view.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downX = event.rawX
                    downY = event.rawY
                    startX = params.x
                    startY = params.y
                    false
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = (startX - (event.rawX - downX).toInt()).coerceAtLeast(0)
                    params.y = (startY + (event.rawY - downY).toInt()).coerceAtLeast(0)
                    try { windowManager.updateViewLayout(view, params) } catch (_: Exception) { }
                    true
                }
                else -> false
            }
        }
    }

    private fun buildHandle(): View {
        return TextView(this).apply {
            text = "◆"
            textSize = 18f
            gravity = Gravity.CENTER
            setTextColor(green)
            background = rounded(dark, green, 25)
            setPadding(dp(12), dp(9), dp(12), dp(9))
            setOnClickListener {
                hudState = HudState.COMPACT
                rebuildOverlayKeepingPosition()
            }
        }
    }

    private fun buildCompactHud(): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(dark, green, 25)
            setPadding(dp(12), dp(7), dp(8), dp(7))
        }
        row.addView(compactText("◆ DJAEGER", green))
        row.addView(compactText("${snapshot.fps} FPS"))
        row.addView(compactText("${snapshot.cpuTemp}°C"))
        row.addView(compactText(snapshot.mode))
        row.addView(compactText("⌄", green).apply {
            setOnClickListener {
                hudState = HudState.EXPANDED
                rebuildOverlayKeepingPosition()
            }
        })
        row.setOnLongClickListener {
            hudState = HudState.HANDLE
            rebuildOverlayKeepingPosition()
            true
        }
        return row
    }

    private fun buildExpandedHud(): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(panel, green, 18)
            setPadding(dp(13), dp(10), dp(13), dp(12))
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(TextView(this).apply {
            text = "◆  DJAEGER GAME TURBO"
            textSize = 14f
            setTextColor(green)
            typeface = Typeface.DEFAULT_BOLD
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        header.addView(actionText("−") {
            hudState = HudState.COMPACT
            rebuildOverlayKeepingPosition()
        })
        header.addView(actionText("×") {
            suppressedForCurrentSession = true
            gameSessionActive = false
            removeOverlay()
        })
        box.addView(header)

        val metrics = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            background = rounded(dark, Color.rgb(34, 64, 44), 12)
            setPadding(dp(8), dp(10), dp(8), dp(10))
        }
        addMetric(metrics, "FPS", snapshot.fps)
        addMetric(metrics, "FRAME", "${snapshot.frameMs} ms")
        addMetric(metrics, "CPU", "${snapshot.cpuTemp}°C")
        addMetric(metrics, "GPU", "${snapshot.gpuTemp}°C")
        box.addView(metrics, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(9) })

        box.addView(TextView(this).apply {
            text = "${snapshot.game}  •  ${snapshot.session.uppercase(Locale.US)}"
            textSize = 11f
            setTextColor(muted)
            setPadding(dp(4), dp(9), 0, dp(7))
        })

        val modes = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS").forEach { mode ->
            val color = modeColor(mode)
            modes.addView(TextView(this).apply {
                text = mode
                textSize = 9f
                gravity = Gravity.CENTER
                setTextColor(color)
                background = rounded(dark, color, 9)
                setPadding(dp(6), dp(8), dp(6), dp(8))
                setOnClickListener { setTrustedMode(mode) }
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(2)
                marginEnd = dp(2)
            })
        }
        box.addView(modes)

        box.addView(TextView(this).apply {
            text = "↔  RESIZE MANUAL"
            textSize = 10f
            gravity = Gravity.CENTER
            setTextColor(muted)
            setPadding(dp(8), dp(10), dp(8), dp(5))
            setOnClickListener {
                manualScale = when {
                    manualScale < 0.9f -> 1.0f
                    manualScale < 1.1f -> 1.2f
                    else -> 0.8f
                }
                overlayView?.scaleX = manualScale
                overlayView?.scaleY = manualScale
            }
        })

        return box
    }

    private fun compactText(value: String, color: Int = Color.WHITE): TextView {
        return TextView(this).apply {
            text = value
            textSize = 12f
            setTextColor(color)
            setPadding(dp(7), 0, dp(7), 0)
        }
    }

    private fun actionText(value: String, action: () -> Unit): TextView {
        return TextView(this).apply {
            text = value
            textSize = 18f
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            setPadding(dp(10), dp(5), dp(10), dp(5))
            setOnClickListener { action() }
        }
    }

    private fun addMetric(parent: LinearLayout, label: String, value: String) {
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

    private fun modeColor(mode: String): Int = when (mode) {
        "AUTO" -> green
        "DINGIN" -> Color.rgb(60, 150, 255)
        "SEDANG" -> Color.rgb(255, 205, 45)
        "HANGAT" -> Color.rgb(255, 145, 35)
        else -> Color.rgb(242, 70, 75)
    }

    private fun setTrustedMode(mode: String) {
        val argument = when (mode) {
            "AUTO" -> "auto"
            "DINGIN" -> "dingin"
            "SEDANG" -> "sedang"
            "HANGAT" -> "hangat"
            "PANAS" -> "panas"
            else -> return
        }
        thread(name = "djaeger-mode") { runRoot("djaeger-ai mode $argument") }
    }

    private fun rounded(fill: Int, stroke: Int, radiusDp: Int): GradientDrawable {
        return GradientDrawable().apply {
            setColor(fill)
            cornerRadius = dp(radiusDp).toFloat()
            setStroke(dp(1), stroke)
        }
    }

    private fun runRoot(command: String): String = try {
        val process = ProcessBuilder("su", "-c", command).redirectErrorStream(true).start()
        val output = BufferedReader(InputStreamReader(process.inputStream)).use { it.readText() }
        process.waitFor()
        output
    } catch (_: Exception) {
        ""
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun pxToDp(value: Int): Int = (value / resources.displayMetrics.density).toInt()
}
''')

m = pkg / 'MainActivity.kt'
s = m.read_text()
s = s.replace('GAMING TURBO • v0.8.2 RC • GAME TURBO • REALTIME 1s', 'GAMING TURBO • v0.8.3 RC • GAME TURBO • REALTIME 1s')
s = s.replace('DJAEGER v0.8.2 RC', 'DJAEGER v0.8.3 RC')
m.write_text(s)
