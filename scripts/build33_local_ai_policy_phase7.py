from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 33', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.7-rc-local-ai-policy-phase7"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.6 RC • LOAD + BOTTLENECK PHASE 6 • REALTIME 1s',
                'GAMING TURBO • v0.11.7 RC • LOCAL AI POLICY PHASE 7 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.6 RC', 'DJAEGER v0.11.7 RC')
m.write_text(ms)

anchor = '''    private data class SceneAssessment(\n        val state: SceneState = SceneState.UNKNOWN,\n        val confidence: Int = 0,\n        val source: String = "INSUFFICIENT_SIGNALS"\n    )\n\n'''
if anchor not in s:
    raise SystemExit('Build33: SceneAssessment anchor missing')
policy_types = '''    private enum class PolicyIntent { OBSERVE, STABILIZE_FRAME, RELIEVE_CPU, RELIEVE_GPU, THERMAL_RECOVERY }\n\n    private data class AdaptivePolicy(\n        val intent: PolicyIntent = PolicyIntent.OBSERVE,\n        val confidence: Int = 0,\n        val reason: String = "INSUFFICIENT_SIGNALS",\n        val executor: String = "DJAEGER_AI_TYPED_INTENT"\n    )\n\n'''
s = s.replace(anchor, anchor + policy_types, 1)

old_runtime = '''        val cpuLoad: String = "--",\n        val gpuLoad: String = "--",\n        val loadSource: String = "UNAVAILABLE"\n'''
new_runtime = '''        val cpuLoad: String = "--",\n        val gpuLoad: String = "--",\n        val loadSource: String = "UNAVAILABLE",\n        val policy: AdaptivePolicy = AdaptivePolicy()\n'''
if old_runtime not in s:
    raise SystemExit('Build33: RuntimeSnapshot phase6 anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

# Policy continuity: emit only on stable scene changes and never every 1s poll.
anchor = '    private var freeformTransitionHoldUntil = 0L\n'
if anchor not in s:
    raise SystemExit('Build33: policy continuity anchor missing')
s = s.replace(anchor, anchor + '''    private var lastPolicyScene = SceneState.UNKNOWN\n    private var stablePolicyScene = SceneState.UNKNOWN\n    private var policySceneVotes = 0\n    private var lastPolicyDispatchAt = 0L\n    private var lastPolicyIntent = PolicyIntent.OBSERVE\n''', 1)

# Typed mapping: Control Center expresses intent only. It never writes sysfs or
# invents CPU/GPU frequencies. djaeger-ai remains the root/local executor and
# therefore retains live capability, snapshot, rollback and read-back authority.
parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build33: parseSnapshot anchor missing')
policy_logic = r'''    private fun deriveAdaptivePolicy(scene: SceneAssessment): AdaptivePolicy {
        if (scene.confidence < 65) return AdaptivePolicy()
        return when (scene.state) {
            SceneState.CPU_BOUND -> AdaptivePolicy(PolicyIntent.RELIEVE_CPU, scene.confidence, scene.source)
            SceneState.GPU_BOUND -> AdaptivePolicy(PolicyIntent.RELIEVE_GPU, scene.confidence, scene.source)
            SceneState.FRAME_BOUND, SceneState.HIGH_LOAD -> AdaptivePolicy(PolicyIntent.STABILIZE_FRAME, scene.confidence, scene.source)
            SceneState.THERMAL_BOUND -> AdaptivePolicy(PolicyIntent.THERMAL_RECOVERY, scene.confidence, scene.source)
            else -> AdaptivePolicy(PolicyIntent.OBSERVE, scene.confidence, scene.source)
        }
    }

    private fun dispatchAdaptivePolicy(snapshot: RuntimeSnapshot) {
        if (!gameSessionActive) return
        val scene = snapshot.scene.state
        if (scene == lastPolicyScene) policySceneVotes++ else {
            lastPolicyScene = scene
            policySceneVotes = 1
        }
        if (policySceneVotes < 3) return
        stablePolicyScene = scene

        val policy = snapshot.policy
        if (policy.intent == PolicyIntent.OBSERVE || policy.confidence < 65) return
        val now = android.os.SystemClock.elapsedRealtime()
        if (policy.intent == lastPolicyIntent && now - lastPolicyDispatchAt < 12_000L) return

        // All fields are locally generated enum/numeric values, not Gemini/raw user
        // shell text. The executor receives a strict typed key=value envelope.
        val intent = policy.intent.name
        val sceneName = scene.name
        val confidence = policy.confidence.coerceIn(0, 100)
        val cpu = snapshot.cpuLoad.toDoubleOrNull()?.coerceIn(0.0, 100.0)
        val gpu = snapshot.gpuLoad.toDoubleOrNull()?.coerceIn(0.0, 100.0)
        val payload = buildString {
            append("SCHEMA=DJAEGER_LOCAL_POLICY_V1")
            append(" INTENT=").append(intent)
            append(" SCENE=").append(sceneName)
            append(" CONFIDENCE=").append(confidence)
            if (cpu != null) append(" CPU_LOAD=").append(String.format(Locale.US, "%.1f", cpu))
            if (gpu != null) append(" GPU_LOAD=").append(String.format(Locale.US, "%.1f", gpu))
        }
        lastPolicyDispatchAt = now
        lastPolicyIntent = policy.intent
        thread(name = "djaeger-local-policy") {
            // Prefer the typed policy endpoint. If this module generation does not
            // expose it yet, no direct sysfs fallback is allowed from the APK.
            runRoot("command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-intent '$payload' >/dev/null 2>&1 || true")
        }
    }

'''
s = s.replace(parse_anchor, policy_logic + parse_anchor, 1)

old_scene = '        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu, cpuLoad, gpuLoad)\n'
new_scene = '''        val scene = assessScene(runtime, fps, frame, jank, cpu, gpu, cpuLoad, gpuLoad)\n        val policy = deriveAdaptivePolicy(scene)\n'''
if old_scene not in s:
    raise SystemExit('Build33: phase6 scene call missing')
s = s.replace(old_scene, new_scene, 1)

old_return = '''            gpuLoad?.let { one(it) } ?: "--",\n            loadSource\n        )\n'''
new_return = '''            gpuLoad?.let { one(it) } ?: "--",\n            loadSource, policy\n        )\n'''
if old_return not in s:
    raise SystemExit('Build33: phase6 RuntimeSnapshot tail missing')
s = s.replace(old_return, new_return, 1)

# Dispatch after an in-place telemetry update. This preserves anti-flicker and
# decouples policy execution from WindowManager lifecycle.
old_update = '''        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n    }\n'''
new_update = '''        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n        dispatchAdaptivePolicy(snapshot)\n    }\n'''
if old_update not in s:
    raise SystemExit('Build33: updateOverlayContent tail missing')
s = s.replace(old_update, new_update, 1)

# Show policy intent in the existing scene footer without adding another overlay
# object or rebuilding WindowManager.
s = s.replace(
    'panelScene?.text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    'panelScene?.text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace(\'_\', \' \')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    1
)
s = s.replace(
    'text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    'text = "${snapshot.scene.state.name.replace(\'_\', \' \')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace(\'_\', \' \')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"',
    1
)

required = [
    'PolicyIntent { OBSERVE, STABILIZE_FRAME, RELIEVE_CPU, RELIEVE_GPU, THERMAL_RECOVERY }',
    'DJAEGER_LOCAL_POLICY_V1', 'djaeger-ai policy-intent',
    'policySceneVotes < 3', '12_000L',
    'SceneState.CPU_BOUND', 'SceneState.GPU_BOUND', 'SceneState.FRAME_BOUND', 'SceneState.THERMAL_BOUND',
    'PROC_STAT+KGSL', 'dumpsys SurfaceFlinger --latency',
    'private fun updateOverlayContent()', 'freeformTransitionHoldUntil',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build33 regression: required marker missing: {marker}')

# APK is control plane only: no direct actuator/sysfs writes or arbitrary shell
# generated from Gemini/user text in this policy path.
policy_body = s.split('private fun dispatchAdaptivePolicy(snapshot: RuntimeSnapshot)',1)[1].split('private fun parseSnapshot',1)[0]
for forbidden in ('/sys/', 'echo ', 'printf ', 'settings put', 'setprop', 'eval ', 'source '):
    if forbidden in policy_body:
        raise SystemExit(f'Build33 authority regression in policy path: {forbidden}')
if "djaeger-ai policy-intent '$payload'" not in policy_body:
    raise SystemExit('Build33: typed executor endpoint missing')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build33 anti-flicker regression: {forbidden_call}')

h.write_text(s)
print('Build 33 phase 7 applied: typed Local AI adaptive policy intents with hysteresis/cooldown; no APK sysfs writes')
