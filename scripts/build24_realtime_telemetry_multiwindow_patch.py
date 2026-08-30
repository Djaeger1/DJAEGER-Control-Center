from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Version bump.
g = Path('app/build.gradle.kts')
s = g.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 24', s, count=1)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.10.2-rc-realtime-telemetry-multiwindow"', s, count=1)
g.write_text(s)

m = pkg / 'MainActivity.kt'
s = m.read_text()
s = s.replace(
    'GAMING TURBO • v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC • REALTIME 1s',
    'GAMING TURBO • v0.10.2 RC • REALTIME TELEMETRY + MULTI WINDOW • 1s'
)
s = s.replace('DJAEGER v0.10.1 RC', 'DJAEGER v0.10.2 RC')
m.write_text(s)

h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

# Imports required by icon launcher and precise parsing.
imports = {
    'import android.content.Intent\n': 'import android.content.Intent\nimport android.content.ComponentName\n',
    'import android.graphics.drawable.GradientDrawable\n': 'import android.graphics.drawable.GradientDrawable\nimport android.graphics.drawable.Drawable\n',
    'import android.widget.LinearLayout\n': 'import android.widget.LinearLayout\nimport android.widget.HorizontalScrollView\nimport android.widget.ImageView\nimport android.widget.Toast\n',
}
for old, new in imports.items():
    if old not in s:
        raise SystemExit(f'Build24: import anchor missing: {old!r}')
    s = s.replace(old, new, 1)

# Track whether the app-icon strip is visible.
anchor = '    private var manualScale = 1.0f\n'
if anchor not in s:
    raise SystemExit('Build24: manualScale anchor missing')
s = s.replace(anchor, anchor + '    private var multiWindowMenuVisible = false\n', 1)

# Replace the old telemetry file poll. The old v0.10.1 reader pointed at
# /data/adb/djaeger_ai/telemetry.csv, while DJAEGER v12.9.50 writes telemetry.csv
# under /data/adb/modules/djaeger_game_stabilizer/. Build24 samples temperatures
# directly from read-only thermal sysfs and SurfaceFlinger presentation timestamps
# every ACTIVE poll, with the module CSV as a fallback only.
old_raw = '''                val raw = runRoot(
                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +
                        "echo __DJAEGER_TELEMETRY__; " +
                        "tail -n 1 /data/adb/djaeger_ai/telemetry.csv 2>/dev/null"
                )
'''
new_raw = '''                val raw = runRoot(
                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +
                        "echo __DJAEGER_THERMAL__; " +
                        "for z in /sys/class/thermal/thermal_zone*; do " +
                        "[ -r \\\"$z/type\\\" ] || continue; [ -r \\\"$z/temp\\\" ] || continue; " +
                        "read -r n < \\\"$z/type\\\"; case \\\"$n\\\" in " +
                        "cpu-*-usr|cpuss-*-usr|gpuss-*-usr) read -r t < \\\"$z/temp\\\"; printf '%s=%s\\\\n' \\\"$n\\\" \\\"$t\\\";; esac; done; " +
                        "echo __DJAEGER_LATENCY__; " +
                        "L=\\\"$(cat /data/adb/djaeger_ai/frame_layer 2>/dev/null)\\\"; " +
                        "[ -n \\\"$L\\\" ] && dumpsys SurfaceFlinger --latency \\\"$L\\\" 2>/dev/null; " +
                        "echo __DJAEGER_CSV__; " +
                        "tail -n 1 /data/adb/modules/djaeger_game_stabilizer/telemetry.csv 2>/dev/null"
                )
'''
if old_raw not in s:
    raise SystemExit('Build24: telemetry poll anchor missing')
s = s.replace(old_raw, new_raw, 1)

# Replace parser with a source-aware parser. SurfaceFlinger uses presentation
# timestamps; the most recent 30 valid frame intervals (~0.5 s at 60 fps) are
# averaged for near-realtime FPS/frame-time. CPU/GPU temperatures come from the
# same thermal-zone types used by the controller. CSV uses the real v12.9.50
# schema: frame_ms index 9, fps_est index 10.
start = s.find('    private fun parseSnapshot(raw: String): RuntimeSnapshot {')
end = s.find('\n    private fun showOverlay()', start)
if start < 0 or end < 0:
    raise SystemExit('Build24: parseSnapshot block missing')
new_parser = r'''    private fun parseSnapshot(raw: String): RuntimeSnapshot {
        val runtimeText = raw.substringBefore("__DJAEGER_THERMAL__")
        val thermalText = raw.substringAfter("__DJAEGER_THERMAL__", "")
            .substringBefore("__DJAEGER_LATENCY__")
        val latencyText = raw.substringAfter("__DJAEGER_LATENCY__", "")
            .substringBefore("__DJAEGER_CSV__")
        val csvText = raw.substringAfter("__DJAEGER_CSV__", "").trim()

        val runtime = runtimeText.lineSequence().mapNotNull { line ->
            val split = line.indexOf('=')
            if (split <= 0) null else {
                val key = line.substring(0, split).trim().lowercase(Locale.US)
                val value = line.substring(split + 1).trim().trim('"', '\'')
                key to value
            }
        }.toMap()

        fun thermalC(rawValue: String?): Double? {
            val value = rawValue?.trim()?.toDoubleOrNull() ?: return null
            return if (kotlin.math.abs(value) > 1000.0) value / 1000.0 else value
        }
        var cpuNow: Double? = null
        var gpuNow: Double? = null
        thermalText.lineSequence().forEach { line ->
            val split = line.indexOf('=')
            if (split <= 0) return@forEach
            val type = line.substring(0, split).trim()
            val temp = thermalC(line.substring(split + 1)) ?: return@forEach
            when {
                type == "gpuss-0-usr" || type.startsWith("gpuss-") ->
                    gpuNow = maxOf(gpuNow ?: temp, temp)
                type.startsWith("cpu-") || type.startsWith("cpuss-") ->
                    cpuNow = maxOf(cpuNow ?: temp, temp)
            }
        }

        // Parse SurfaceFlinger --latency. Column 2 is the presentation timestamp
        // in ns. Work on the newest 31 timestamps -> newest 30 frame intervals.
        val present = latencyText.lineSequence().drop(1).mapNotNull { line ->
            val c = line.trim().split(Regex("\\s+"))
            c.getOrNull(1)?.toLongOrNull()?.takeIf { it > 0L }
        }.toList()
        val intervals = present.zipWithNext { a, b -> (b - a) / 1_000_000.0 }
            .filter { it in 4.0..250.0 }
            .takeLast(30)
        val liveFrame = intervals.takeIf { it.size >= 3 }?.average()
        val liveFps = liveFrame?.takeIf { it > 0.0 }?.let { 1000.0 / it }

        // Real DJAEGER v12.9.50 CSV fallback schema:
        // 0 epoch, 1 cpu_t, 2 gpu_t, ... 9 frame_ms, 10 fps_est, ...
        val csv = csvText.split(',')
        fun csvNumber(index: Int): Double? = csv.getOrNull(index)?.trim()?.toDoubleOrNull()
        val csvCpu = csvNumber(1)
        val csvGpu = csvNumber(2)
        val csvFrame = csvNumber(9)
        val csvFps = csvNumber(10)

        val fpsValue = liveFps ?: csvFps
        val frameValue = liveFrame ?: csvFrame
        val cpuValue = cpuNow ?: csvCpu
        val gpuValue = gpuNow ?: csvGpu

        fun oneDecimal(value: Double?): String = value?.takeIf { it.isFinite() }?.let {
            String.format(Locale.US, "%.1f", it)
        } ?: "--"
        fun tempDisplay(value: Double?): String = value?.takeIf { it.isFinite() }?.let {
            String.format(Locale.US, "%.0f", it)
        } ?: "--"

        val game = runtime["game"] ?: runtime["game_id"] ?: runtime["package"] ?: "NA"
        val mode = runtime["user_mode"] ?: runtime["mode"] ?: "AUTO"
        val window = runtime["window_mode"] ?: runtime["window"] ?: runtime["window_state"] ?: "INACTIVE"
        val activeFlag = runtime["active"]?.lowercase(Locale.US) in setOf("1", "true", "active")
        val session = runtime["session"] ?: runtime["session_state"]
            ?: if (activeFlag || window.equals("ACTIVE", true)) "ACTIVE" else "INACTIVE"

        return RuntimeSnapshot(
            fps = oneDecimal(fpsValue),
            frameMs = oneDecimal(frameValue),
            cpuTemp = tempDisplay(cpuValue),
            gpuTemp = tempDisplay(gpuValue),
            mode = mode.uppercase(Locale.US),
            game = game,
            window = window,
            session = session
        )
    }
'''
s = s[:start] + new_parser + s[end:]

# Add a visible multi-window icon in the expanded HUD header.
old_header = '''        header.addView(actionText("−") {
            hudState = HudState.COMPACT
            rebuildOverlayKeepingPosition()
        })
        header.addView(actionText("×") {
'''
new_header = '''        header.addView(actionText("▦") {
            multiWindowMenuVisible = !multiWindowMenuVisible
            rebuildOverlayKeepingPosition()
        })
        header.addView(actionText("−") {
            hudState = HudState.COMPACT
            rebuildOverlayKeepingPosition()
        })
        header.addView(actionText("×") {
'''
if old_header not in s:
    raise SystemExit('Build24: expanded header anchor missing')
s = s.replace(old_header, new_header, 1)

# Insert icon launcher strip after the mode buttons. This is user-triggered and
# may rebuild once when opening/closing the menu; polling itself never rebuilds.
anchor = '        box.addView(modes)\n\n        box.addView(TextView(this).apply {'
if anchor not in s:
    raise SystemExit('Build24: modes insertion anchor missing')
insert = '''        box.addView(modes)

        if (multiWindowMenuVisible) {
            box.addView(buildMultiWindowMenu())
        }

        box.addView(TextView(this).apply {'''
s = s.replace(anchor, insert, 1)

# Insert multi-window helpers before compactText().
anchor = '    private fun compactText(value: String, color: Int = Color.WHITE): TextView {\n'
if anchor not in s:
    raise SystemExit('Build24: compactText helper anchor missing')
helpers = r'''    private fun buildMultiWindowMenu(): View {
        val outer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(2), dp(8), dp(2), dp(2))
        }
        outer.addView(TextView(this).apply {
            text = "MULTI WINDOW"
            textSize = 9f
            setTextColor(muted)
            setPadding(dp(4), 0, 0, dp(5))
        })

        val launcherIntent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val activities = packageManager.queryIntentActivities(launcherIntent, 0)
            .filter { it.activityInfo.packageName != packageName }
            .distinctBy { it.activityInfo.packageName }
            .sortedBy { it.loadLabel(packageManager).toString().lowercase(Locale.US) }
            .take(12)

        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        activities.forEach { info ->
            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(dp(4), dp(3), dp(4), dp(3))
            }
            item.addView(ImageView(this).apply {
                setImageDrawable(info.loadIcon(packageManager))
                scaleType = ImageView.ScaleType.FIT_CENTER
            }, LinearLayout.LayoutParams(dp(34), dp(34)))
            item.addView(TextView(this).apply {
                val label = info.loadLabel(packageManager).toString()
                text = if (label.length > 8) label.take(7) + "…" else label
                textSize = 8f
                gravity = Gravity.CENTER
                setTextColor(Color.WHITE)
                maxLines = 1
            }, LinearLayout.LayoutParams(dp(54), LinearLayout.LayoutParams.WRAP_CONTENT))
            item.setOnClickListener {
                launchFreeform(
                    info.activityInfo.packageName,
                    info.activityInfo.name,
                    info.loadLabel(packageManager).toString()
                )
            }
            row.addView(item)
        }

        if (activities.isEmpty()) {
            row.addView(TextView(this).apply {
                text = "Tidak ada launcher app yang terlihat"
                textSize = 9f
                setTextColor(muted)
                setPadding(dp(4), dp(5), dp(4), dp(5))
            })
        }

        return HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            addView(row)
        }.also { outer.addView(it) }.let { outer }
    }

    private fun launchFreeform(pkg: String, activity: String, label: String) {
        val safePkg = pkg.replace(Regex("[^A-Za-z0-9._]"), "")
        val safeActivity = activity.replace(Regex("[^A-Za-z0-9._$]"), "")
        if (safePkg.isBlank() || safeActivity.isBlank()) return
        thread(name = "djaeger-multiwindow") {
            val output = runRoot(
                "am start --user 0 --windowingMode 5 -n " +
                    safePkg + "/" + safeActivity + " 2>&1; echo __DJAEGER_RC__$?"
            )
            val ok = output.lineSequence().any { it.trim() == "__DJAEGER_RC__0" }
            mainHandler.post {
                Toast.makeText(
                    this,
                    if (ok) "$label → multi window" else "Multi window ditolak sistem untuk $label",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# Static invariants: telemetry is read-only; active polling still updates attached views in place.
if '/data/adb/djaeger_ai/telemetry.csv' in s:
    raise SystemExit('Build24: stale telemetry path still present')
if '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv' not in s:
    raise SystemExit('Build24: module telemetry fallback path missing')
if 'csvNumber(9)' not in s or 'csvNumber(10)' not in s:
    raise SystemExit('Build24: correct frame/fps CSV indexes missing')
if 'dumpsys SurfaceFlinger --latency' not in s:
    raise SystemExit('Build24: SurfaceFlinger realtime path missing')
if 'am start --user 0 --windowingMode 5' not in s:
    raise SystemExit('Build24: freeform launch path missing')

h.write_text(s)

# Android package visibility: allow discovery of launcher activities without QUERY_ALL_PACKAGES.
manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text()
if '<queries>' not in ms:
    app_anchor = '<application'
    pos = ms.find(app_anchor)
    if pos < 0:
        raise SystemExit('Build24: manifest application anchor missing')
    queries = '''    <queries>\n        <intent>\n            <action android:name="android.intent.action.MAIN" />\n            <category android:name="android.intent.category.LAUNCHER" />\n        </intent>\n    </queries>\n\n'''
    ms = ms[:pos] + queries + ms[pos:]
manifest.write_text(ms)

print('Build 24 realtime telemetry + multi-window launcher applied')
