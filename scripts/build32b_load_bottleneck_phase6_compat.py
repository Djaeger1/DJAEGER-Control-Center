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

old_scene_enum = 'private enum class SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, THERMAL_BOUND }'
new_scene_enum = 'private enum class SceneState { UNKNOWN, LOADING_CANDIDATE, GAMEPLAY, HIGH_LOAD, FRAME_BOUND, CPU_BOUND, GPU_BOUND, THERMAL_BOUND }'
if old_scene_enum not in s:
    raise SystemExit('Build32b: Phase5 scene enum missing')
s = s.replace(old_scene_enum, new_scene_enum, 1)

old_runtime = '''        val session: String = "INACTIVE",\n        val scene: SceneAssessment = SceneAssessment()\n'''
new_runtime = '''        val session: String = "INACTIVE",\n        val scene: SceneAssessment = SceneAssessment(),\n        val cpuLoad: String = "--",\n        val gpuLoad: String = "--",\n        val loadSource: String = "UNAVAILABLE"\n'''
if old_runtime not in s:
    raise SystemExit('Build32b: RuntimeSnapshot Phase5 anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

poll_anchor = '                        "echo __DJAEGER_LATENCY__; " +\n'
if poll_anchor not in s:
    raise SystemExit('Build32b: latency command anchor missing')
load_probe = '''                        "echo __DJAEGER_LOAD__; " +\n                        "read -r _ u n sy id io irq sirq st _ < /proc/stat; " +\n                        "T1=${'$'}((u+n+sy+id+io+irq+sirq+st)); I1=${'$'}((id+io)); sleep 0.12; " +\n                        "read -r _ u n sy id io irq sirq st _ < /proc/stat; " +\n                        "T2=${'$'}((u+n+sy+id+io+irq+sirq+st)); I2=${'$'}((id+io)); " +\n                        "DT=${'$'}((T2-T1)); DI=${'$'}((I2-I1)); [ \\\"${'$'}DT\\\" -gt 0 ] && printf 'CPU_LOAD=%s\\\\n' \\\"${'$'}(((DT-DI)*100/DT))\\\"; " +\n                        "for g in /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage /sys/class/kgsl/kgsl-3d0/gpuload /sys/class/kgsl/kgsl-3d0/devfreq/gpu_load; do " +\n                        "[ -r \\\"${'$'}g\\\" ] || continue; read -r gl < \\\"${'$'}g\\\"; printf 'GPU_LOAD_RAW=%s\\\\n' \\\"${'$'}gl\\\"; printf 'GPU_LOAD_PATH=%s\\\\n' \\\"${'$'}g\\\"; break; done; " +\n'''
s = s.replace(poll_anchor, load_probe + poll_anchor, 1)

start = s.find('    private fun assessScene(')
end = s.find('\n    private fun parseSnapshot(raw: String): RuntimeSnapshot {', start)
if start < 0 or end < 0:
    raise SystemExit('Build32b: assessScene boundaries missing')
classifier = r'''    private fun assessScene(
        runtime: Map<String, String>, fps: Double?, frameMs: Double?, jankPct: Double?,
        cpuTemp: Double?, gpuTemp: Double?, cpuLoad: Double?, gpuLoad: Double?
    ): SceneAssessment {
        val cause = listOfNotNull(runtime["cause"], runtime["thermal_state"], runtime["state_reason"])
            .joinToString(" ").lowercase(Locale.US)
        if ("thermal" in cause || "overheat" in cause || "throttle" in cause)
            return SceneAssessment(SceneState.THERMAL_BOUND, 95, "RUNTIME_THERMAL_SIGNAL")

        val framePressure = frameMs != null && (frameMs >= 20.0 || (jankPct ?: 0.0) >= 8.0)
        if (framePressure && cpuLoad != null && gpuLoad != null) {
            if (gpuLoad >= 88.0 && cpuLoad <= 78.0)
                return SceneAssessment(SceneState.GPU_BOUND, 86, "KGSL_HIGH_CPU_HEADROOM")
            if (cpuLoad >= 88.0 && gpuLoad <= 72.0)
                return SceneAssessment(SceneState.CPU_BOUND, 84, "CPU_HIGH_GPU_HEADROOM")
            if (cpuLoad >= 78.0 && gpuLoad >= 78.0)
                return SceneAssessment(SceneState.FRAME_BOUND, 78, "CPU_GPU_PRESSURE")
        }
        if (framePressure && (jankPct ?: 0.0) >= 12.0)
            return SceneAssessment(SceneState.FRAME_BOUND, 70, "FRAME_JANK_WITHOUT_CLEAR_DEVICE_BOUND")
        if (fps != null && frameMs != null) {
            if ((jankPct ?: 0.0) >= 20.0 || frameMs >= 35.0)
                return SceneAssessment(SceneState.HIGH_LOAD, 68, "FRAME_TIME_JANK")
            if (fps < 18.0 && frameMs >= 45.0)
                return SceneAssessment(SceneState.LOADING_CANDIDATE, 45, "LOW_FPS_LONG_FRAME")
            if (fps >= 24.0 && frameMs in 4.0..42.0)
                return SceneAssessment(SceneState.GAMEPLAY, 68, "ACTIVE_FRAME_STREAM")
        }
        @Suppress("UNUSED_VARIABLE") val tempsObserved = cpuTemp != null || gpuTemp != null
        return SceneAssessment(SceneState.UNKNOWN, 20, "INSUFFICIENT_SIGNALS")
    }
'''
s = s[:start] + classifier + s[end:]

# Current Build26/31 source names this section latencyText, not latencyPart.
latency_anchor_candidates = [
    '        val latencyText = raw.substringAfter("__DJAEGER_LATENCY__", "").substringBefore("__DJAEGER_CSV__")\n',
    '        val latencyText = raw.substringAfter("__DJAEGER_LATENCY__", "").substringBefore("__DJAEGER_CSV__", "")\n',
]
latency_anchor = next((a for a in latency_anchor_candidates if a in s), None)
if latency_anchor is None:
    raise SystemExit('Build32b: current latencyText parser anchor missing')
parse_load = '''        val loadPart = raw.substringAfter("__DJAEGER_LOAD__", "").substringBefore("__DJAEGER_LATENCY__", "")\n        val loadMap = loadPart.lineSequence().mapNotNull { line ->\n            val p = line.indexOf('='); if (p <= 0) null else line.substring(0, p).trim() to line.substring(p + 1).trim()\n        }.toMap()\n        val cpuLoad = loadMap["CPU_LOAD"]?.toDoubleOrNull()?.takeIf { it in 0.0..100.0 }\n        val gpuRaw = loadMap["GPU_LOAD_RAW"]?.trim()?.substringBefore(' ')?.toDoubleOrNull()\n        val gpuLoad = when {\n            gpuRaw == null -> null\n            gpuRaw in 0.0..100.0 -> gpuRaw\n            gpuRaw in 0.0..10000.0 -> gpuRaw / 100.0\n            else -> null\n        }?.coerceIn(0.0, 100.0)\n        val loadSource = when {\n            cpuLoad != null && gpuLoad != null -> "PROC_STAT+KGSL"\n            cpuLoad != null -> "PROC_STAT"\n            gpuLoad != null -> "KGSL"\n            else -> "UNAVAILABLE"\n        }\n'''
s = s.replace(latency_anchor, parse_load + latency_anchor, 1)

old_call = '        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu)\n'
new_call = '        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu, cpuLoad, gpuLoad)\n'
if old_call not in s:
    raise SystemExit('Build32b: Phase5 assessScene call missing')
s = s.replace(old_call, new_call, 1)

old_tail = '''            game, window, session, scene\n        )\n'''
new_tail = '''            game, window, session, scene,\n            cpuLoad?.let { one(it) } ?: "--",\n            gpuLoad?.let { one(it) } ?: "--",\n            loadSource\n        )\n'''
if old_tail not in s:
    raise SystemExit('Build32b: RuntimeSnapshot return tail missing')
s = s.replace(old_tail, new_tail, 1)

required = [
    'FRAME_BOUND, CPU_BOUND, GPU_BOUND, THERMAL_BOUND',
    'echo __DJAEGER_LOAD__', '/proc/stat', '/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage',
    'SceneState.CPU_BOUND', 'SceneState.GPU_BOUND', 'SceneState.FRAME_BOUND',
    'PROC_STAT+KGSL', 'loadSource', 'dumpsys SurfaceFlinger --latency',
    'freeformTransitionHoldUntil', 'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build32b regression: {marker}')
if 'framePressure && cpuLoad != null && gpuLoad != null' not in s:
    raise SystemExit('Build32b: bottleneck confidence gate missing')

h.write_text(s)
print('Build 32b compatibility phase applied: proc-stat/KGSL load + current latencyText parser + bottleneck classification')
