package com.djaeger.observer

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private val bg = Color.rgb(7,10,15)
    private val panel = Color.rgb(17,22,30)
    private val green = Color.rgb(34,227,154)
    private val white = Color.rgb(239,244,248)
    private val muted = Color.rgb(162,174,188)
    private lateinit var list: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render(emptyMap())
        handler.post(refresh)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private val refresh = object : Runnable {
        override fun run() {
            thread {
                val raw = root("cat /data/adb/djaeger_observer/runtime/snapshot.env 2>/dev/null; echo __BUS__; cat /data/adb/djaeger_observer/runtime/agent_bus.env 2>/dev/null; echo __EXEC__; cat /data/adb/djaeger_observer/runtime/executor.env 2>/dev/null")
                val map = parse(raw)
                handler.post { render(map) }
            }
            handler.postDelayed(this, 2000)
        }
    }

    private fun parse(raw: String): Map<String,String> =
        raw.lineSequence().mapNotNull {
            if (it.startsWith("__")) return@mapNotNull null
            val p = it.indexOf('=')
            if (p <= 0) null else it.substring(0,p).trim() to it.substring(p+1).trim()
        }.toMap()

    private fun render(s: Map<String,String>) {
        list = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(18), dp(16), dp(28))
            setBackgroundColor(bg)
        }

        list.addView(TextView(this).apply {
            text = "DJAEGER AI"
            textSize = 28f
            setTextColor(green)
            typeface = Typeface.DEFAULT_BOLD
        })
        list.addView(TextView(this).apply {
            text = "OBSERVER ENGINE • OVERVIEW"
            textSize = 12f
            setTextColor(muted)
            setPadding(0, dp(2), 0, dp(16))
        })

        card("STATUS",
            "Engine      ${v(s,"ENGINE","OFFLINE")}\n" +
            "Package     ${v(s,"ACTIVE_PACKAGE","UNKNOWN")}\n" +
            "Learning    ${v(s,"LEARNING_STATE","WAITING")}\n" +
            "Migration   ${v(s,"MIGRATION_STATE","UNKNOWN")}")

        card("THOUGHT",
            "Gemini: ${v(s,"GEMINI","NOT_FOUND")}\n" +
            "Active brain: HERMES LOCAL + HERMES CLOUD + GEMINI\n" +
            "Cloud in control: CONSENSUS ONLY\n" +
            "Cloud plan: ${v(s,"POLICY_STATE","OBSERVING")}")

        card("HERMES",
            "Hermes Local   ${v(s,"HERMES_LOCAL","WAITING")}\n" +
            "Hermes Cloud   ${v(s,"HERMES_CLOUD","WAITING")}\n" +
            "AI Bus         ${v(s,"AI_BUS","WAITING")}\n" +
            "Legacy config  ${v(s,"LEGACY_CONFIG_PRESENT","NO")}")

        card("HERMES CTX1 • CONTEXT VNEXT • SHADOW",
            "CPU avg      ${v(s,"CPU_AVG_KHZ","--")} kHz\n" +
            "CPU live     ${v(s,"CPU_CUR_MIN_KHZ","--")}–${v(s,"CPU_CUR_MAX_KHZ","--")} kHz\n" +
            "GPU          ${v(s,"GPU_CUR_HZ","--")}\n" +
            "Skin         ${v(s,"SKIN_TEMP_C","--")} °C\n" +
            "Battery      ${v(s,"BATTERY_TEMP_C","--")} °C • ${v(s,"BATTERY_PCT","--")}%\n" +
            "Power        ${v(s,"POWER_MW","--")} mW")

        card("STRATEGY",
            "Baseline      STOCK\n" +
            "Legacy preset DISABLED\n" +
            "Policy        ${v(s,"POLICY_STATE","OBSERVING")}\n" +
            "Executor      ${v(s,"EXECUTOR_STATE","OBSERVE_ONLY")}\n" +
            "Authority     ${v(s,"HARDWARE_AUTHORITY","VALIDATED_EXECUTOR_ONLY")}")

        card("OUTCOME LEARNING",
            "Sample        ${v(s,"SAMPLE_SEQ","0")}\n" +
            "Learning      ${v(s,"LEARNING_STATE","WAITING")}\n" +
            "Rule          compare against stock before apply\n" +
            "Rollback      required for every adaptive policy")

        val scroll = ScrollView(this)
        scroll.addView(list)
        setContentView(scroll)
    }

    private fun v(s: Map<String,String>, key:String, fallback:String) =
        s[key]?.takeIf { it.isNotBlank() } ?: fallback

    private fun card(title:String, body:String) {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(13))
            background = GradientDrawable().apply {
                setColor(panel)
                cornerRadius = dp(17).toFloat()
                setStroke(dp(1), Color.rgb(38,58,55))
            }
        }
        box.addView(TextView(this).apply {
            text = title
            textSize = 13f
            setTextColor(green)
            typeface = Typeface.DEFAULT_BOLD
        })
        box.addView(TextView(this).apply {
            text = body
            textSize = 13f
            setLineSpacing(0f, 1.18f)
            setTextColor(white)
            setPadding(0, dp(8), 0, 0)
        })
        list.addView(box, LinearLayout.LayoutParams(-1,-2).apply { bottomMargin = dp(10) })
    }

    private fun dp(v:Int) = (v * resources.displayMetrics.density).toInt()

    private fun root(cmd:String):String = try {
        val p = ProcessBuilder("su","-c",cmd).redirectErrorStream(true).start()
        BufferedReader(InputStreamReader(p.inputStream)).use { it.readText() }.also { p.waitFor() }
    } catch (_:Exception) { "" }
}
