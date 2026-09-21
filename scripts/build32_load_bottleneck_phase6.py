from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 32', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.6-rc-load-bottleneck-phase6"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.5 RC • SESSION + SCENE PHASE 5 • REALTIME 1s',
                'GAMING TURBO • v0.11.6 RC • LOAD + BOTTLENECK PHASE 6 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.5 RC', 'DJAEGER v0.11.6 RC')
m.write_text(ms)

s = s.replace(
    'private enum class SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, THERMAL_BOUND }',
    'private enum class SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, FRAME_BOUND, CPU_BOUND, GPU_BOUND, THERMAL_BOUND }',
    1
)

old_runtime = '''        val session: String = "INACTIVE",\n        val scene: SceneAssessment = SceneAssessment()\n'''
new_runtime = '''        val session: String = "INACTIVE",\n        val scene: SceneAssessment = SceneAssessment(),\n        val cpuLoad: String = "--",\n        val gpuLoad: String = "--",\n        val loadSource: String = "UNAVAILABLE"\n'''
if old_runtime not in s:
    raise SystemExit('Build32: RuntimeSnapshot phase5 anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

# CPU utilization is sampled from /proc/stat deltas, not inferred from frequency.
# GPU utilization uses the first readable KGSL source and is normalized later.
poll_anchor = '                        "echo __DJAEGER_LATENCY__; " +\n'
if poll_anchor not in s:
    raise SystemExit('Build32: poll telemetry anchor missing')
load_probe = '''                        "echo __DJAEGER_LOAD__; " +\n                        "read -r _ u n sy id io irq sirq st _ < /proc/stat; " +\n                        "T1=${'$'}((u+n+sy+id+io+irq+sirq+st)); I1=${'$'}((id+io)); sleep 0.12; " +\n                        "read -r _ u n sy id io irq sirq st _ < /proc/stat; " +\n                        "T2=${'$'}((u+n+sy+id+io+irq+sirq+st)); I2=${'$'}((id+io)); " +\n                        "DT=${'$'}((T2-T1)); DI=${'$'}((I2-I1)); [ \\\"${'$'}DT\\\" -gt 0 ] && printf 'CPU_LOAD=%s\\\\n' \\\"${'$'}(((DT-DI)*100/DT))\\\"; " +\n                        "for g in /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage /sys/class/kgsl/kgsl-3d0/gpuload /sys/class/kgsl/kgsl-3d0/devfreq/gpu_load; do " +\n                        "[ -r \\\"${'$'}g\\\" ] || continue; read -r gl < \\\"${'$'}g\\\"; printf 'GPU_LOAD_RAW=%s\\\\n' \\\"${'$'}gl\\\"; printf 'GPU_LOAD_PATH=%s\\\\n' \\\"${'$'}g\\\"; break; done; " +\n'''
s = s.replace(poll_anchor, load_probe + poll_anchor, 1)

# Replace scene classifier with load-aware but confidence-gated classification.
start = s.find('    private fun assessScene(')
end = s.find('\n    private fun parseSnapshot(raw: String): RuntimeSnapshot {', start)
if start < 0 or end < 0:
    raise SystemExit('Build32: assessScene boundaries missing')
classifier = r'''    private fun assessScene(
        runtime: Map<String, String>,
        fps: Double?,
        frameMs: Double?,
        jankPct: Double?,
        cpuTemp: Double?,
        gpuTemp: Double?,
        cpuLoad: Double?,
        gpuLoad: Double?
    ): SceneAssessment {
        val cause = listOfNotNull(runtime["cause"], runtime["thermal_state"], runtime["state_reason"])
            .joinToString(" ").lowercase(Locale.US)
        if ("thermal" in cause || "overheat" in cause || "throttle" in cause) {
            return SceneAssessment(SceneState.THERMAL_BOUND, 95, "RUNTIME_THERMAL_SIGNAL")
        }

        val framePressure = frameMs != null && (frameMs >= 20.0 || (jankPct ?: 0.0) >= 8.0)
        if (framePressure && cpuLoad != null && gpuLoad != null) {
            if (gpuLoad >= 88.0 && cpuLoad <= 78.0) {
                return SceneAssessment(SceneState.GPU_BOUND, 86, "KGSL_HIGH_CPU_HEADROOM")
            }
            if (cpuLoad >= 88.0 && gpuLoad <= 72.0) {
                return SceneAssessment(SceneState.CPU_BOUND, 84, "CPU_HIGH_GPU_HEADROOM")
            }
            if (cpuLoad >= 78.0 && gpuLoad >= 78.0) {
                return SceneAssessment(SceneState.FRAME_BOUND, 78, "CPU_GPU_PRESSURE")
            }
        }
        if (framePressure && (jankPct ?: 0.0) >= 12.0) {
            return SceneAssessment(SceneState.FRAME_BOUND, 70, "FRAME_JANK_WITHOUT_CLEAR_DEVICE_BOUND")
        }
        if (fps != null && frameMs != null) {
            if ((jankPct ?: 0.0) >= 20.0 || frameMs >= 35.0) {
                return SceneAssessment(SceneState.HIGH_LOAD, 68, "FRAME_TIME_JANK")
            }
            if (fps < 18.0 && frameMs >= 45.0) {
                return SceneAssessment(SceneState.LOADING_CANDIDATE, 45, "LOW_FPS_LONG_FRAME")
            }
            if (fps >= 24.0 && frameMs in 4.0..42.0) {
                return SceneAssessment(SceneState.GAMEPLAY, 68, "ACTIVE_FRAME_STREAM")
            }
        }
        @Suppress("UNUSED_VARIABLE") val tempsObserved = cpuTemp != null || gpuTemp != null
        return SceneAssessment(SceneState.UNKNOWN, 20, "INSUFFICIENT_SIGNALS")
    }
'''
s = s[:start] + classifier + s[end:]

# Parse the load section independently from latency/CSV blocks.
parse_marker = '''        val latencyPart = raw.substringAfter("__DJAEGER_LATENCY__", "").substringBefore("__DJAEGER_CSV__", "")\n'''
if parse_marker not in s:
    raise SystemExit('Build32: latency parser anchor missing')
parse_load = '''        val loadPart = raw.substringAfter("__DJAEGER_LOAD__", "").substringBefore("__DJAEGER_LATENCY__", "")\n        val loadMap = loadPart.lineSequence().mapNotNull { line ->\n            val p = line.indexOf('='); if (p <= 0) null else line.substring(0, p).trim() to line.substring(p + 1).trim()\n        }.toMap()\n        val cpuLoad = loadMap["CPU_LOAD"]?.toDoubleOrNull()?.takeIf { it in 0.0..100.0 }\n        val gpuRaw = loadMap["GPU_LOAD_RAW"]?.trim()?.substringBefore(' ')?.toDoubleOrNull()\n        val gpuPath = loadMap["GPU_LOAD_PATH"].orEmpty()\n        val gpuLoad = when {\n            gpuRaw == null -> null\n            gpuRaw in 0.0..100.0 -> gpuRaw\n            gpuRaw in 0.0..10000.0 -> gpuRaw / 100.0\n            else -> null\n        }?.coerceIn(0.0, 100.0)\n        val loadSource = when {\n            cpuLoad != null && gpuLoad != null -> "PROC_STAT+KGSL"\n            cpuLoad != null -> "PROC_STAT"\n            gpuLoad != null -> "KGSL"\n            else -> "UNAVAILABLE"\n        }\n'''
s = s.replace(parse_marker, parse_load + parse_marker, 1)

old_scene = '        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu)\n'
new_scene = '        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu, cpuLoad, gpuLoad)\n'
if old_scene not in s:
    raise SystemExit('Build32: phase5 scene call missing')
s = s.replace(old_scene, new_scene, 1)

old_return = '''            game, window, session, scene\n        )\n'''
new_return = '''            game, window, session, scene,\n            cpuLoad?.let { one(it) } ?: "--",\n            gpuLoad?.let { one(it) } ?: "--",\n            loadSource\n        )\n'''
if old_return not in s:
    raise SystemExit('Build32: phase5 RuntimeSnapshot return tail missing')
s = s.replace(old_return, new_return, 1)

# Scene footer includes real load values when available, without inventing numbers.
s = s.replace(
    'panelScene?.text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}%"',
    'panelScene?.text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    1
)
s = s.replace(
    'text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}%"',
    'text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    1
)

required = [
    'FRAME_BOUND, CPU_BOUND, GPU_BOUND, THERMAL_BOUND',
    'echo __DJAEGER_LOAD__', '/proc/stat',
    '/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage',
    '/sys/class/kgsl/kgsl-3d0/gpuload',
    '/sys/class/kgsl/kgsl-3d0/devfreq/gpu_load',
    'SceneState.CPU_BOUND', 'SceneState.GPU_BOUND', 'SceneState.FRAME_BOUND',
    'PROC_STAT+KGSL', 'loadSource',
    'private fun updateOverlayContent()', 'dumpsys SurfaceFlinger --latency',
    'freeformTransitionHoldUntil',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")',
    'djaeger-ai mode'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build32 regression: required marker missing: {marker}')

# Bottleneck claims must require frame pressure and real load samples.
if 'framePressure && cpuLoad != null && gpuLoad != null' not in s:
    raise SystemExit('Build32: bottleneck confidence gate missing')
apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body:
    raise SystemExit('Build32: in-place session update missing')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build32: anti-flicker invariant broken: {forbidden_call}')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build32: forbidden unrelated mutation present: {forbidden}')

h.write_text(s)
print('Build 32 phase 6 applied: proc-stat CPU load + KGSL GPU load + confidence-gated bottleneck classification')
