from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Version: monitoring-only reset based on the proven Control Center codebase.
g = Path('app/build.gradle.kts')
s = g.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 38', s, count=1)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.0.0-monitoring-edition"', s, count=1)
g.write_text(s)

# Replace the activity with a read-only dashboard. No mode buttons, no HUD,
# no sysfs writes, no service control, no game launching.
(pkg / 'MainActivity.kt').write_text(r'''package com.djaeger.controlcenter

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlin.concurrent.thread
import kotlin.math.abs

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private var running = false
    private var inFlight = false

    private val bg = Color.rgb(5, 10, 17)
    private val panel = Color.rgb(10, 18, 29)
    private val panel2 = Color.rgb(13, 24, 38)
    private val accent = Color.rgb(47, 195, 255)
    private val green = Color.rgb(72, 224, 150)
    private val amber = Color.rgb(255, 191, 71)
    private val red = Color.rgb(255, 100, 112)
    private val white = Color.rgb(240, 247, 255)
    private val muted = Color.rgb(150, 171, 193)

    private lateinit var healthChip: TextView
    private lateinit var kernelValue: TextView
    private lateinit var moduleValue: TextView
    private lateinit var geminiValue: TextView
    private lateinit var ksuValue: TextView
    private lateinit var cpuLittleValue: TextView
    private lateinit var cpuBigValue: TextView
    private lateinit var gpuValue: TextView
    private lateinit var cpuGovValue: TextView
    private lateinit var gpuGovValue: TextView
    private lateinit var cpuTempValue: TextView
    private lateinit var gpuTempValue: TextView
    private lateinit var skinTempValue: TextView
    private lateinit var fpsValue: TextView
    private lateinit var frameValue: TextView
    private lateinit var jankValue: TextView
    private lateinit var batteryValue: TextView
    private lateinit var currentValue: TextView
    private lateinit var voltageValue: TextView
    private lateinit var powerValue: TextView
    private lateinit var chargeValue: TextView
    private lateinit var panelCoolValue: TextView
    private lateinit var batteryCoolValue: TextView
    private lateinit var sessionValue: TextView
    private lateinit var updatedValue: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        setContentView(buildDashboard())
    }

    override fun onResume() {
        super.onResume()
        running = true
        handler.post(refreshRunnable)
    }

    override fun onPause() {
        running = false
        handler.removeCallbacksAndMessages(null)
        super.onPause()
    }

    private val refreshRunnable = object : Runnable {
        override fun run() {
            if (!running) return
            if (!inFlight) {
                inFlight = true
                thread(name = "djaeger-monitor") {
                    val snapshot = readSnapshot()
                    runOnUiThread {
                        render(snapshot)
                        inFlight = false
                        if (running) handler.postDelayed(this, 1000L)
                    }
                }
            } else {
                handler.postDelayed(this, 250L)
            }
        }
    }

    private fun buildDashboard(): View {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(bg)
            isFillViewport = true
            overScrollMode = View.OVER_SCROLL_NEVER
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(20), dp(18), dp(28))
        }
        scroll.addView(root)

        val hero = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(17))
            background = rounded(panel, accent, 22, 1)
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        top.addView(TextView(this).apply {
            text = "DJAEGER"
            textSize = 24f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.08f
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        healthChip = chip("SCANNING", amber)
        top.addView(healthChip)
        hero.addView(top)
        hero.addView(TextView(this).apply {
            text = "CONTROL CENTER"
            textSize = 13f
            setTextColor(accent)
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.12f
            setPadding(0, dp(2), 0, 0)
        })
        hero.addView(TextView(this).apply {
            text = "Monitoring Edition • Kernel + DJAEGER telemetry"
            textSize = 12f
            setTextColor(muted)
            setPadding(0, dp(8), 0, 0)
        })
        root.addView(hero, fullMargins(0, 0, 0, 16))

        root.addView(sectionTitle("SYSTEM CORE"))
        val system = card()
        kernelValue = valueLine(system, "Kernel", "--")
        moduleValue = valueLine(system, "DJAEGER module", "--")
        geminiValue = valueLine(system, "Gemini", "--")
        ksuValue = valueLine(system, "Root / KernelSU", "--")
        sessionValue = valueLine(system, "Session", "--")
        root.addView(system, fullMargins(0, 7, 0, 16))

        root.addView(sectionTitle("LIVE PERFORMANCE"))
        val perf = card()
        perf.addView(metricRow(
            metric("CPU LITTLE", "--", "MHz").also { cpuLittleValue = it },
            metric("CPU BIG", "--", "MHz").also { cpuBigValue = it },
            metric("GPU", "--", "MHz").also { gpuValue = it }
        ))
        perf.addView(divider())
        cpuGovValue = valueLine(perf, "CPU governor", "--")
        gpuGovValue = valueLine(perf, "GPU governor", "--")
        root.addView(perf, fullMargins(0, 7, 0, 16))

        root.addView(sectionTitle("THERMAL"))
        val thermal = card()
        thermal.addView(metricRow(
            metric("CPU", "--", "°C").also { cpuTempValue = it },
            metric("GPU", "--", "°C").also { gpuTempValue = it },
            metric("SKIN", "--", "°C").also { skinTempValue = it }
        ))
        root.addView(thermal, fullMargins(0, 7, 0, 16))

        root.addView(sectionTitle("FRAME TELEMETRY"))
        val frameCard = card()
        frameCard.addView(metricRow(
            metric("FPS", "--", "").also { fpsValue = it },
            metric("FRAME", "--", "ms").also { frameValue = it },
            metric("JANK", "--", "%").also { jankValue = it }
        ))
        root.addView(frameCard, fullMargins(0, 7, 0, 16))

        root.addView(sectionTitle("BATTERY & POWER"))
        val bat = card()
        bat.addView(metricRow(
            metric("BATTERY", "--", "%").also { batteryValue = it },
            metric("VOLTAGE", "--", "V").also { voltageValue = it },
            metric("POWER", "--", "W").also { powerValue = it }
        ))
        bat.addView(divider())
        currentValue = valueLine(bat, "Current", "--")
        chargeValue = valueLine(bat, "Charge state", "--")
        root.addView(bat, fullMargins(0, 7, 0, 16))

        root.addView(sectionTitle("PROTECTED ACTUATORS • READ ONLY"))
        val protected = card()
        panelCoolValue = valueLine(protected, "Panel cooling", "--")
        batteryCoolValue = valueLine(protected, "Battery cooling", "--")
        protected.addView(TextView(this).apply {
            text = "Control Center hanya membaca node ini. Tidak ada write, restore, atau override dari aplikasi."
            textSize = 11f
            setTextColor(muted)
            setPadding(0, dp(10), 0, 0)
        })
        root.addView(protected, fullMargins(0, 7, 0, 16))

        updatedValue = TextView(this).apply {
            text = "Waiting for telemetry…"
            textSize = 11f
            setTextColor(muted)
            gravity = Gravity.CENTER
        }
        root.addView(updatedValue, fullMargins(0, 2, 0, 0))
        return scroll
    }

    private data class Snapshot(
        val root: Boolean,
        val kernel: String,
        val module: String,
        val gemini: String,
        val ksu: String,
        val littleKhz: Long?,
        val bigKhz: Long?,
        val gpuHz: Long?,
        val cpuGov: String,
        val gpuGov: String,
        val cpuTemp: Double?,
        val gpuTemp: Double?,
        val skinTemp: Double?,
        val fps: Double?,
        val frameMs: Double?,
        val jank: Double?,
        val battery: Int?,
        val currentUa: Long?,
        val voltageUv: Long?,
        val batteryStatus: String,
        val panelCooling: String,
        val batteryCooling: String,
        val session: String
    )

    private fun readSnapshot(): Snapshot {
        val raw = runRoot("""
            echo __ROOT__
            id 2>/dev/null
            echo __KERNEL__
            uname -r 2>/dev/null
            echo __MODULE__
            if [ -f /data/adb/modules/djaeger_game_stabilizer/module.prop ]; then grep -E '^(version|versionCode)=' /data/adb/modules/djaeger_game_stabilizer/module.prop 2>/dev/null; else echo MISSING; fi
            echo __GEMINI__
            djaeger-ai gemini-status 2>/dev/null | head -n 8
            echo __KSU__
            if [ -d /data/adb/ksu ] || [ -e /data/adb/ksud ]; then echo DETECTED; else echo ROOT_AVAILABLE; fi
            echo __CPU__
            cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq 2>/dev/null
            cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq 2>/dev/null
            cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor 2>/dev/null
            echo __GPU__
            cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null
            cat /sys/class/kgsl/kgsl-3d0/devfreq/governor 2>/dev/null
            echo __THERMAL__
            for z in /sys/class/thermal/thermal_zone*; do
              [ -r "$z/type" ] || continue; [ -r "$z/temp" ] || continue
              n=$(cat "$z/type" 2>/dev/null); t=$(cat "$z/temp" 2>/dev/null)
              case "$n" in cpu-*-usr|cpuss-*-usr|gpuss-*-usr|skin*|quiet-therm-usr) printf '%s=%s\n' "$n" "$t";; esac
            done
            echo __BATTERY__
            cat /sys/class/power_supply/battery/capacity 2>/dev/null
            cat /sys/class/power_supply/battery/current_now 2>/dev/null
            cat /sys/class/power_supply/battery/voltage_now 2>/dev/null
            cat /sys/class/power_supply/battery/status 2>/dev/null
            echo __COOLING__
            cat /sys/class/thermal/cooling_device17/cur_state 2>/dev/null
            cat /sys/class/thermal/cooling_device17/max_state 2>/dev/null
            cat /sys/class/thermal/cooling_device16/cur_state 2>/dev/null
            cat /sys/class/thermal/cooling_device16/max_state 2>/dev/null
            echo __RUNTIME__
            cat /data/adb/djaeger_ai/runtime_status 2>/dev/null | head -n 40
            echo __CSV__
            tail -n 1 /data/adb/modules/djaeger_game_stabilizer/telemetry.csv 2>/dev/null
        """.trimIndent())

        fun section(name: String, next: String): String = raw.substringAfter(name, "").substringBefore(next, "")
        val rootSection = section("__ROOT__", "__KERNEL__")
        val kernel = section("__KERNEL__", "__MODULE__").trim().lineSequence().firstOrNull().orEmpty()
        val moduleText = section("__MODULE__", "__GEMINI__").trim()
        val geminiText = section("__GEMINI__", "__KSU__").trim()
        val ksuText = section("__KSU__", "__CPU__").trim()
        val cpu = section("__CPU__", "__GPU__").trim().lines()
        val gpu = section("__GPU__", "__THERMAL__").trim().lines()
        val thermal = section("__THERMAL__", "__BATTERY__")
        val battery = section("__BATTERY__", "__COOLING__").trim().lines()
        val cooling = section("__COOLING__", "__RUNTIME__").trim().lines()
        val runtime = section("__RUNTIME__", "__CSV__")
        val csv = raw.substringAfter("__CSV__", "").trim().lineSequence().firstOrNull().orEmpty().split(',')

        fun normTemp(v: String?): Double? {
            val n = v?.trim()?.toDoubleOrNull() ?: return null
            return if (abs(n) > 1000.0) n / 1000.0 else n
        }
        var cpuT: Double? = null; var gpuT: Double? = null; var skinT: Double? = null
        thermal.lineSequence().forEach { line ->
            val p = line.indexOf('='); if (p <= 0) return@forEach
            val type = line.substring(0, p); val t = normTemp(line.substring(p + 1)) ?: return@forEach
            when {
                type.startsWith("gpuss-") -> gpuT = maxOf(gpuT ?: t, t)
                type.startsWith("cpu-") || type.startsWith("cpuss-") -> cpuT = maxOf(cpuT ?: t, t)
                type.startsWith("skin") || type.startsWith("quiet-therm") -> skinT = maxOf(skinT ?: t, t)
            }
        }
        fun csvNum(i: Int): Double? = csv.getOrNull(i)?.trim()?.toDoubleOrNull()
        val runtimeMap = runtime.lineSequence().mapNotNull { line ->
            val p = line.indexOf('='); if (p <= 0) null else line.substring(0,p).trim().lowercase() to line.substring(p+1).trim().trim('\'', '"')
        }.toMap()
        val session = runtimeMap["session"] ?: runtimeMap["session_state"] ?: runtimeMap["window_mode"] ?: "INACTIVE"

        return Snapshot(
            root = rootSection.contains("uid=0"),
            kernel = kernel.ifBlank { "Unknown" },
            module = moduleText.lineSequence().firstOrNull { it.startsWith("version=") }?.substringAfter('=') ?: if (moduleText.contains("MISSING")) "Not installed" else "Detected",
            gemini = when {
                geminiText.contains("HTTP_CODE=200") || geminiText.contains("AVAILABLE", true) -> "Available"
                geminiText.isBlank() -> "Unknown"
                else -> geminiText.lineSequence().firstOrNull()?.take(28) ?: "Unknown"
            },
            ksu = ksuText.lineSequence().firstOrNull()?.trim().orEmpty().ifBlank { if (rootSection.contains("uid=0")) "Root available" else "Unavailable" },
            littleKhz = cpu.getOrNull(0)?.toLongOrNull(),
            bigKhz = cpu.getOrNull(1)?.toLongOrNull(),
            cpuGov = cpu.getOrNull(2).orEmpty().ifBlank { "--" },
            gpuHz = gpu.getOrNull(0)?.toLongOrNull(),
            gpuGov = gpu.getOrNull(1).orEmpty().ifBlank { "--" },
            cpuTemp = cpuT ?: csvNum(1), gpuTemp = gpuT ?: csvNum(2), skinTemp = skinT ?: csvNum(3),
            fps = csvNum(10), frameMs = csvNum(9), jank = csvNum(12),
            battery = battery.getOrNull(0)?.toIntOrNull(),
            currentUa = battery.getOrNull(1)?.toLongOrNull(), voltageUv = battery.getOrNull(2)?.toLongOrNull(),
            batteryStatus = battery.getOrNull(3).orEmpty().ifBlank { "--" },
            panelCooling = if (cooling.size >= 2) "${cooling[0]}/${cooling[1]}" else "--",
            batteryCooling = if (cooling.size >= 4) "${cooling[2]}/${cooling[3]}" else "--",
            session = session.uppercase()
        )
    }

    private fun render(s: Snapshot) {
        healthChip.text = if (s.root) "READ ONLY • LIVE" else "ROOT NEEDED"
        healthChip.background = rounded(if (s.root) Color.argb(36,72,224,150) else Color.argb(42,255,100,112), if (s.root) green else red, 18, 1)
        healthChip.setTextColor(if (s.root) green else red)

        kernelValue.text = s.kernel
        moduleValue.text = s.module
        geminiValue.text = s.gemini
        ksuValue.text = s.ksu
        sessionValue.text = s.session
        cpuLittleValue.text = mhzFromKhz(s.littleKhz)
        cpuBigValue.text = mhzFromKhz(s.bigKhz)
        gpuValue.text = mhzFromHz(s.gpuHz)
        cpuGovValue.text = s.cpuGov
        gpuGovValue.text = s.gpuGov
        cpuTempValue.text = one(s.cpuTemp)
        gpuTempValue.text = one(s.gpuTemp)
        skinTempValue.text = one(s.skinTemp)
        fpsValue.text = one(s.fps)
        frameValue.text = one(s.frameMs)
        jankValue.text = one(s.jank)
        batteryValue.text = s.battery?.toString() ?: "--"
        val amps = s.currentUa?.let { it / 1_000_000.0 }
        currentValue.text = amps?.let { String.format("%.3f A", it) } ?: "--"
        val volts = s.voltageUv?.let { it / 1_000_000.0 }
        voltageValue.text = volts?.let { String.format("%.2f", it) } ?: "--"
        val watts = if (amps != null && volts != null) abs(amps * volts) else null
        powerValue.text = watts?.let { String.format("%.2f", it) } ?: "--"
        chargeValue.text = s.batteryStatus
        panelCoolValue.text = s.panelCooling
        batteryCoolValue.text = s.batteryCooling
        panelCoolValue.setTextColor(if (s.panelCooling.startsWith("0/")) green else amber)
        batteryCoolValue.setTextColor(if (s.batteryCooling.startsWith("0/")) green else amber)
        updatedValue.text = "Live refresh 1s • monitoring-only • no hardware writes"
    }

    private fun runRoot(command: String): String = try {
        val p = ProcessBuilder("su", "-c", command).redirectErrorStream(true).start()
        val out = p.inputStream.bufferedReader().use { it.readText() }
        p.waitFor()
        out
    } catch (_: Throwable) { "" }

    private fun sectionTitle(text: String) = TextView(this).apply {
        this.text = text
        textSize = 11f
        setTextColor(accent)
        typeface = Typeface.DEFAULT_BOLD
        letterSpacing = 0.11f
    }

    private fun card() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(15), dp(14), dp(15), dp(14))
        background = rounded(panel2, Color.argb(75, 85, 119, 150), 18, 1)
    }

    private fun metric(label: String, value: String, unit: String): TextView {
        return TextView(this).apply {
            text = value
            textSize = 24f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            tag = unit
            contentDescription = label
            setPadding(dp(4), dp(25), dp(4), dp(8))
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(14).toFloat()
                setColor(Color.rgb(9, 19, 31))
            }
            // Label is rendered as a small sibling overlay-like header through a compound string below.
            hint = "$label${if (unit.isNotBlank()) " • $unit" else ""}"
            setHintTextColor(muted)
        }
    }

    private fun metricRow(a: TextView, b: TextView, c: TextView): View {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf(a,b,c).forEachIndexed { i, v ->
            row.addView(v, LinearLayout.LayoutParams(0, dp(88), 1f).apply {
                if (i > 0) leftMargin = dp(8)
            })
        }
        return row
    }

    private fun valueLine(parent: LinearLayout, label: String, initial: String): TextView {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(7), 0, dp(7))
        }
        row.addView(TextView(this).apply {
            text = label
            textSize = 12f
            setTextColor(muted)
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        val value = TextView(this).apply {
            text = initial
            textSize = 12f
            setTextColor(white)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.END
            maxLines = 1
        }
        row.addView(value, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.45f))
        parent.addView(row)
        return value
    }

    private fun divider() = View(this).apply {
        setBackgroundColor(Color.argb(70, 86, 114, 139))
    }.also { it.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)).apply { topMargin = dp(12); bottomMargin = dp(6) } }

    private fun chip(text: String, color: Int) = TextView(this).apply {
        this.text = text
        textSize = 10f
        setTextColor(color)
        typeface = Typeface.DEFAULT_BOLD
        gravity = Gravity.CENTER
        setPadding(dp(10), dp(6), dp(10), dp(6))
        background = rounded(Color.argb(34, Color.red(color), Color.green(color), Color.blue(color)), color, 18, 1)
    }

    private fun rounded(fill: Int, stroke: Int, radius: Int, strokeWidth: Int = 0) = GradientDrawable().apply {
        shape = GradientDrawable.RECTANGLE
        cornerRadius = dp(radius).toFloat()
        setColor(fill)
        if (strokeWidth > 0) setStroke(dp(strokeWidth), stroke)
    }

    private fun fullMargins(l: Int, t: Int, r: Int, b: Int) = LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
    ).apply { setMargins(dp(l), dp(t), dp(r), dp(b)) }

    private fun mhzFromKhz(v: Long?): String = v?.let { (it / 1000L).toString() } ?: "--"
    private fun mhzFromHz(v: Long?): String = v?.let { (it / 1_000_000L).toString() } ?: "--"
    private fun one(v: Double?): String = v?.takeIf { it.isFinite() }?.let { String.format("%.1f", it) } ?: "--"
    private fun dp(v: Int): Int = (v * resources.displayMetrics.density + 0.5f).toInt()
}
''')

# Keep the historical class available for any stale compile-time references, but
# make it inert. It is not declared in the final manifest.
(pkg / 'DjaegerHudService.kt').write_text(r'''package com.djaeger.controlcenter

import android.app.Service
import android.content.Intent
import android.os.IBinder

/** Legacy compatibility stub. Monitoring Edition never starts or declares it. */
class DjaegerHudService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        stopSelf()
        return START_NOT_STICKY
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
''')

# Strip control/HUD permissions and components from the final manifest while
# preserving MainActivity launcher declaration.
manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text()
for permission in [
    'android.permission.SYSTEM_ALERT_WINDOW',
    'android.permission.PACKAGE_USAGE_STATS',
    'android.permission.FOREGROUND_SERVICE',
    'android.permission.RECEIVE_BOOT_COMPLETED'
]:
    ms = re.sub(r'\s*<uses-permission[^>]*android:name="' + re.escape(permission) + r'"[^>]*/>\s*', '\n', ms)

# Remove explicit service/receiver blocks added by previous Game Turbo stages.
ms = re.sub(r'\s*<service\b[^>]*android:name="\.DjaegerHudService"[^>]*/>\s*', '\n', ms, flags=re.S)
ms = re.sub(r'\s*<service\b[^>]*android:name="com\.djaeger\.controlcenter\.DjaegerHudService"[^>]*/>\s*', '\n', ms, flags=re.S)
ms = re.sub(r'\s*<service\b[^>]*android:name="\.DjaegerHudService"[^>]*>.*?</service>\s*', '\n', ms, flags=re.S)
ms = re.sub(r'\s*<receiver\b[^>]*android:name="\.BootReceiver"[^>]*/>\s*', '\n', ms, flags=re.S)
ms = re.sub(r'\s*<receiver\b[^>]*android:name="\.BootReceiver"[^>]*>.*?</receiver>\s*', '\n', ms, flags=re.S)
manifest.write_text(ms)

# Source-level invariants: application has zero hardware/control mutations.
activity = (pkg / 'MainActivity.kt').read_text()
for forbidden in [
    'echo 0 >', 'echo 1 >', 'settings put', 'setprop', 'force-stop',
    'iptables', 'ip6tables', 'nft ', 'djaeger-ai mode ', 'policy-intent ',
    'native_write_plan', 'TYPE_APPLICATION_OVERLAY', 'SYSTEM_ALERT_WINDOW'
]:
    if forbidden in activity:
        raise SystemExit(f'Build38 monitoring-only violation: {forbidden}')

required = [
    '/sys/class/thermal/cooling_device17/cur_state',
    '/sys/class/thermal/cooling_device16/cur_state',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'djaeger-ai gemini-status',
    'Live refresh 1s • monitoring-only • no hardware writes',
    'PROTECTED ACTUATORS • READ ONLY'
]
for marker in required:
    if marker not in activity:
        raise SystemExit(f'Build38 required monitoring marker missing: {marker}')

print('Build 38 monitoring-only redesign applied')
