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
    raise SystemExit('Build34: AdaptivePolicy anchor missing')
extra = '''    private enum class PolicyExecutionState { IDLE, APPLIED, SUPPRESSED, FAILED, ROLLED_BACK, NOOP, UNAVAILABLE, UNKNOWN }\n\n    private data class PolicyReadback(\n        val state: PolicyExecutionState = PolicyExecutionState.IDLE,\n        val intent: String = "NONE",\n        val scene: String = "UNKNOWN",\n        val confidence: Int = 0,\n        val rootRc: Int? = null,\n        val updatedAt: Long = 0L,\n        val reason: String = "NONE",\n        val executorVersion: String = "UNKNOWN"\n    )\n\n'''
s = s.replace(anchor, anchor + extra, 1)

old_runtime = '''        val loadSource: String = "UNAVAILABLE",\n        val policy: AdaptivePolicy = AdaptivePolicy()\n'''
new_runtime = '''        val loadSource: String = "UNAVAILABLE",\n        val policy: AdaptivePolicy = AdaptivePolicy(),\n        val policyReadback: PolicyReadback = PolicyReadback()\n'''
if old_runtime not in s:
    raise SystemExit('Build34: RuntimeSnapshot policy anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

# Add a root-side handshake/readback probe to the same snapshot command. This is
# read-only and uses the public djaeger-ai status endpoint added by v12.9.51.
old_runtime_cmd = '''printf '__DJAEGER_RUNTIME__\\n'; djaeger-ai runtime 2>/dev/null || true; '''
if old_runtime_cmd not in s:
    # Some generations do not have the exact compact command; insert before CPU stat marker.
    marker = '''printf '__DJAEGER_CPUSTAT__\\n';'''
    if marker not in s:
        raise SystemExit('Build34: snapshot command insertion marker missing')
    s = s.replace(marker,
        '''printf '__DJAEGER_POLICY__\\n'; command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent-status 2>/dev/null || printf "DJAEGER_LOCAL_POLICY_EXECUTOR=UNAVAILABLE\\nSTATE='UNAVAILABLE'\\n"; ''' + marker,
        1)
else:
    s = s.replace(old_runtime_cmd, old_runtime_cmd + '''printf '__DJAEGER_POLICY__\\n'; command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent-status 2>/dev/null || printf "DJAEGER_LOCAL_POLICY_EXECUTOR=UNAVAILABLE\\nSTATE='UNAVAILABLE'\\n"; ''', 1)

parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build34: parseSnapshot anchor missing')
helpers = r'''    private fun parsePolicyReadback(raw: String): PolicyReadback {
        val block = raw.substringAfter("__DJAEGER_POLICY__", "").substringBefore("__DJAEGER_CPUSTAT__", "")
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
            confidence = value("CONFIDENCE")?.toIntOrNull()?.coerceIn(0, 100) ?: 0,
            rootRc = value("ROOT_AUTHORITY_RC")?.toIntOrNull(),
            updatedAt = value("UPDATED_AT")?.toLongOrNull() ?: 0L,
            reason = value("REASON") ?: "NONE",
            executorVersion = version
        )
    }

'''
s = s.replace(parse_anchor, helpers + parse_anchor, 1)

# Parse readback alongside scene/policy. The executor state is authoritative for
# what actually happened; requested policy remains separate.
scene_anchor = '''        val policy = deriveAdaptivePolicy(scene)\n'''
if scene_anchor not in s:
    raise SystemExit('Build34: policy derivation anchor missing')
s = s.replace(scene_anchor, scene_anchor + '''        val policyReadback = parsePolicyReadback(raw)\n''', 1)

old_return = '''            loadSource, policy\n        )\n'''
new_return = '''            loadSource, policy, policyReadback\n        )\n'''
if old_return not in s:
    raise SystemExit('Build34: RuntimeSnapshot return anchor missing')
s = s.replace(old_return, new_return, 1)

# Replace fire-and-forget policy dispatch with an explicit command-result
# handshake. The next normal telemetry poll reads persistent executor status.
old_dispatch = '''        thread(name = "djaeger-local-policy") {\n            // Prefer the typed policy endpoint. If this module generation does not\n            // expose it yet, no direct sysfs fallback is allowed from the APK.\n            runRoot("command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent '$payload' >/dev/null 2>&1 || true")\n        }\n'''
new_dispatch = '''        thread(name = "djaeger-local-policy") {\n            // Request and immediately query the public executor status. No direct\n            // actuator fallback is permitted from the APK.\n            runRoot("command -v djaeger-ai >/dev/null 2>&1 || exit 127; djaeger-ai policy-intent '$payload'; printf '__DJAEGER_POLICY_READBACK__\\n'; djaeger-ai policy-intent-status")\n        }\n'''
if old_dispatch not in s:
    raise SystemExit('Build34: phase7 fire-and-forget dispatch anchor missing')
s = s.replace(old_dispatch, new_dispatch, 1)

# HUD: requested intent and actual executor state are deliberately separate.
old_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_panel not in s:
    raise SystemExit('Build34: panelScene phase7 anchor missing')
s = s.replace(old_panel, new_panel, 1)
old_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_build not in s:
    raise SystemExit('Build34: scene initial text phase7 anchor missing')
s = s.replace(old_build, new_build, 1)

required = [
    'PolicyExecutionState { IDLE, APPLIED, SUPPRESSED, FAILED, ROLLED_BACK, NOOP, UNAVAILABLE, UNKNOWN }',
    '__DJAEGER_POLICY__', 'djaeger-ai policy-intent-status', 'DJAEGER_LOCAL_POLICY_EXECUTOR',
    'ROOT_AUTHORITY_RC', 'PolicyExecutionState.APPLIED', 'PolicyExecutionState.SUPPRESSED',
    'PolicyExecutionState.FAILED', 'PolicyExecutionState.ROLLED_BACK',
    'REQ ${snapshot.policy.intent.name',
    'DJAEGER_LOCAL_POLICY_V1', 'djaeger-ai policy-intent',
    'PROC_STAT+KGSL', 'dumpsys SurfaceFlinger --latency', 'freeformTransitionHoldUntil',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build34 regression: required marker missing: {marker}')

# Readback is read-only. Control Center must remain a control plane, not a root
# actuator implementation.
policy_region = s.split('private fun parsePolicyReadback',1)[1].split('private fun parseSnapshot',1)[0]
for forbidden in ('/sys/', 'settings put', 'setprop', 'echo ', 'eval ', 'source '):
    if forbidden in policy_region:
        raise SystemExit(f'Build34 readback authority regression: {forbidden}')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build34 anti-flicker regression: {forbidden_call}')

h.write_text(s)
print('Build 34 phase 9 applied: runtime policy handshake/readback with requested-vs-actual HUD state')
