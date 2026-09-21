from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 34', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.8-rc-policy-handshake-phase9"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.7 RC • LOCAL AI POLICY PHASE 7 • REALTIME 1s',
                'GAMING TURBO • v0.11.8 RC • POLICY HANDSHAKE PHASE 9 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.7 RC', 'DJAEGER v0.11.8 RC')
m.write_text(ms)

anchor = '''    private data class AdaptivePolicy(\n        val intent: PolicyIntent = PolicyIntent.OBSERVE,\n        val confidence: Int = 0,\n        val reason: String = "INSUFFICIENT_SIGNALS",\n        val executor: String = "DJAEGER_AI_TYPED_INTENT"\n    )\n\n'''
if anchor not in s:
    raise SystemExit('Build34b: AdaptivePolicy anchor missing')
extra = '''    private enum class PolicyExecutionState { IDLE, APPLIED, SUPPRESSED, FAILED, ROLLED_BACK, NOOP, UNAVAILABLE, UNKNOWN }\n\n    private data class PolicyReadback(\n        val state: PolicyExecutionState = PolicyExecutionState.IDLE,\n        val intent: String = "NONE",\n        val scene: String = "UNKNOWN",\n        val confidence: Int = 0,\n        val rootRc: Int? = null,\n        val updatedAt: Long = 0L,\n        val reason: String = "NONE",\n        val executorVersion: String = "UNKNOWN"\n    )\n\n'''
s = s.replace(anchor, anchor + extra, 1)

old_runtime = '''        val loadSource: String = "UNAVAILABLE",\n        val policy: AdaptivePolicy = AdaptivePolicy()\n'''
new_runtime = '''        val loadSource: String = "UNAVAILABLE",\n        val policy: AdaptivePolicy = AdaptivePolicy(),\n        val policyReadback: PolicyReadback = PolicyReadback()\n'''
if old_runtime not in s:
    raise SystemExit('Build34b: RuntimeSnapshot policy anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

# Current runtime command begins by catting runtime_status and then thermal.
cmd_anchor = '                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +\n'
if cmd_anchor not in s:
    raise SystemExit('Build34b: current runtime_status command anchor missing')
policy_probe = '''                    "cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; " +\n                    "echo __DJAEGER_POLICY__; " +\n                    "command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent-status 2>/dev/null || printf 'DJAEGER_LOCAL_POLICY_EXECUTOR=UNAVAILABLE\\\\nSTATE=UNAVAILABLE\\\\n'; " +\n'''
s = s.replace(cmd_anchor, policy_probe, 1)

# Prevent policy key/value output from polluting the runtime_status map.
runtime_parse_old = '        val runtimeText = raw.substringBefore("__DJAEGER_THERMAL__")\n'
runtime_parse_new = '        val runtimeText = raw.substringBefore("__DJAEGER_POLICY__")\n'
if runtime_parse_old not in s:
    raise SystemExit('Build34b: runtimeText parser anchor missing')
s = s.replace(runtime_parse_old, runtime_parse_new, 1)

parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build34b: parseSnapshot anchor missing')
helper = r'''    private fun parsePolicyReadback(raw: String): PolicyReadback {
        val block = raw.substringAfter("__DJAEGER_POLICY__", "").substringBefore("__DJAEGER_THERMAL__", "")
        if (block.isBlank()) return PolicyReadback(state = PolicyExecutionState.UNAVAILABLE)
        fun value(key: String): String? {
            val line = block.lineSequence().firstOrNull { it.startsWith("$key=") } ?: return null
            return line.substringAfter('=').trim().trim('\'', '"')
        }
        val version = value("DJAEGER_LOCAL_POLICY_EXECUTOR") ?: "UNKNOWN"
        val rawState = value("STATE") ?: if (version == "UNAVAILABLE") "UNAVAILABLE" else "IDLE"
        val state = when (rawState.uppercase(Locale.US)) {
            "APPLIED" -> PolicyExecutionState.APPLIED
            "SUPPRESSED" -> PolicyExecutionState.SUPPRESSED
            "FAILED" -> PolicyExecutionState.FAILED
            "ROLLED_BACK", "ROLLBACK_INCOMPLETE" -> PolicyExecutionState.ROLLED_BACK
            "NOOP" -> PolicyExecutionState.NOOP
            "IDLE" -> PolicyExecutionState.IDLE
            "UNAVAILABLE" -> PolicyExecutionState.UNAVAILABLE
            else -> PolicyExecutionState.UNKNOWN
        }
        return PolicyReadback(
            state = state,
            intent = value("INTENT") ?: value("LAST_INTENT") ?: "NONE",
            scene = value("SCENE") ?: "UNKNOWN",
            confidence = value("CONFIDENCE")?.toIntOrNull()?.coerceIn(0,100) ?: 0,
            rootRc = value("ROOT_AUTHORITY_RC")?.toIntOrNull(),
            updatedAt = value("UPDATED_AT")?.toLongOrNull() ?: 0L,
            reason = value("REASON") ?: "NONE",
            executorVersion = version
        )
    }

'''
s = s.replace(parse_anchor, helper + parse_anchor, 1)

policy_anchor = '        val policy = deriveAdaptivePolicy(scene)\n'
if policy_anchor not in s:
    raise SystemExit('Build34b: derived policy anchor missing')
s = s.replace(policy_anchor, policy_anchor + '        val policyReadback = parsePolicyReadback(raw)\n', 1)

old_tail = '''            loadSource, policy\n        )\n'''
new_tail = '''            loadSource, policy, policyReadback\n        )\n'''
if old_tail not in s:
    raise SystemExit('Build34b: RuntimeSnapshot return tail missing')
s = s.replace(old_tail, new_tail, 1)

# Keep typed dispatch, but query status immediately for diagnostics; normal poll
# remains the authoritative persistent readback source.
old_dispatch = '''        thread(name = "djaeger-local-policy") {\n            // Prefer the typed policy endpoint. If this module generation does not\n            // expose it yet, no direct sysfs fallback is allowed from the APK.\n            runRoot("command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent '$payload' >/dev/null 2>&1 || true")\n        }\n'''
new_dispatch = '''        thread(name = "djaeger-local-policy") {\n            runRoot("command -v djaeger-ai >/dev/null 2>&1 || exit 127; djaeger-ai policy-intent '$payload'; printf '__DJAEGER_POLICY_READBACK__\\n'; djaeger-ai policy-intent-status")\n        }\n'''
if old_dispatch not in s:
    raise SystemExit('Build34b: Phase7 dispatch anchor missing')
s = s.replace(old_dispatch, new_dispatch, 1)

old_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_panel not in s:
    raise SystemExit('Build34b: Phase7 panel scene anchor missing')
s = s.replace(old_panel, new_panel, 1)
old_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_build not in s:
    raise SystemExit('Build34b: Phase7 initial scene anchor missing')
s = s.replace(old_build, new_build, 1)

required = [
    '__DJAEGER_POLICY__', 'djaeger-ai policy-intent-status', 'DJAEGER_LOCAL_POLICY_EXECUTOR',
    'ROOT_AUTHORITY_RC', 'PolicyExecutionState.APPLIED', 'PolicyExecutionState.SUPPRESSED',
    'PolicyExecutionState.FAILED', 'PolicyExecutionState.ROLLED_BACK',
    'DJAEGER_LOCAL_POLICY_V1', 'PROC_STAT+KGSL', 'dumpsys SurfaceFlinger --latency',
    'readFreeformState(pkg)', 'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build34b regression: {marker}')

h.write_text(s)
print('Build 34b compatibility handshake applied: runtime_status → policy marker → thermal, persistent executor readback')
