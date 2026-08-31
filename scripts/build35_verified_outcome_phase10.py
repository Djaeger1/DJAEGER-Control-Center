from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 35', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.9-rc-verified-outcome-phase10"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.8 RC • POLICY HANDSHAKE PHASE 9 • REALTIME 1s',
                'GAMING TURBO • v0.11.9 RC • VERIFIED OUTCOME PHASE 10 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.8 RC', 'DJAEGER v0.11.9 RC')
m.write_text(ms)

anchor = '''    private data class PolicyReadback(\n        val state: PolicyExecutionState = PolicyExecutionState.IDLE,\n        val intent: String = "NONE",\n        val scene: String = "UNKNOWN",\n        val confidence: Int = 0,\n        val rootRc: Int? = null,\n        val updatedAt: Long = 0L,\n        val reason: String = "NONE",\n        val executorVersion: String = "UNKNOWN"\n    )\n\n'''
if anchor not in s:
    raise SystemExit('Build35: PolicyReadback anchor missing')
extra = '''    private enum class OutcomeState { PENDING, IMPROVED, NEUTRAL, REGRESSED, INSUFFICIENT_DATA }\n\n    private data class OutcomeSample(\n        val fps: Double?, val frameMs: Double?, val jank: Double?,\n        val cpuTemp: Double?, val gpuTemp: Double?, val cpuLoad: Double?, val gpuLoad: Double?\n    )\n\n    private data class PolicyOutcome(\n        val state: OutcomeState = OutcomeState.INSUFFICIENT_DATA,\n        val score: Int = 0,\n        val reason: String = "NONE",\n        val intent: String = "NONE",\n        val observedMs: Long = 0L\n    )\n\n'''
s = s.replace(anchor, anchor + extra, 1)

old_runtime = '''        val policy: AdaptivePolicy = AdaptivePolicy(),\n        val policyReadback: PolicyReadback = PolicyReadback()\n'''
new_runtime = '''        val policy: AdaptivePolicy = AdaptivePolicy(),\n        val policyReadback: PolicyReadback = PolicyReadback(),\n        val outcome: PolicyOutcome = PolicyOutcome()\n'''
if old_runtime not in s:
    raise SystemExit('Build35: RuntimeSnapshot phase9 anchor missing')
s = s.replace(old_runtime, new_runtime, 1)

state_anchor = '    private var lastPolicyIntent = PolicyIntent.OBSERVE\n'
if state_anchor not in s:
    raise SystemExit('Build35: phase7 state anchor missing')
s = s.replace(state_anchor, state_anchor + '''    private var outcomeBaseline: OutcomeSample? = null\n    private var outcomeBaselineIntent = "NONE"\n    private var outcomeStartedAt = 0L\n    private var outcomePolls = 0\n    private var lastOutcome = PolicyOutcome()\n''', 1)

parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build35: parseSnapshot anchor missing')
helpers = r'''    private fun outcomeSample(snapshot: RuntimeSnapshot): OutcomeSample = OutcomeSample(
        snapshot.fps.toDoubleOrNull(), snapshot.frameMs.toDoubleOrNull(), snapshot.jank.toDoubleOrNull(),
        snapshot.cpuTemp.toDoubleOrNull(), snapshot.gpuTemp.toDoubleOrNull(),
        snapshot.cpuLoad.toDoubleOrNull(), snapshot.gpuLoad.toDoubleOrNull()
    )

    private fun evaluateOutcome(before: OutcomeSample, after: OutcomeSample, intent: String, elapsed: Long): PolicyOutcome {
        // Require frame evidence. Temperature/load are supporting signals, never
        // sufficient alone to declare performance improvement.
        val bf = before.fps; val af = after.fps
        val bm = before.frameMs; val am = after.frameMs
        val bj = before.jank; val aj = after.jank
        if (bf == null || af == null || bm == null || am == null)
            return PolicyOutcome(OutcomeState.INSUFFICIENT_DATA, 0, "FRAME_DATA_MISSING", intent, elapsed)

        var score = 0
        val fpsDelta = af - bf
        val frameDelta = bm - am
        if (fpsDelta >= 2.0) score += 2 else if (fpsDelta <= -2.0) score -= 2
        if (frameDelta >= 0.8) score += 2 else if (frameDelta <= -0.8) score -= 2
        if (bj != null && aj != null) {
            val jankDelta = bj - aj
            if (jankDelta >= 2.0) score += 2 else if (jankDelta <= -2.0) score -= 2
        }
        val beforeThermal = listOfNotNull(before.cpuTemp, before.gpuTemp).maxOrNull()
        val afterThermal = listOfNotNull(after.cpuTemp, after.gpuTemp).maxOrNull()
        if (beforeThermal != null && afterThermal != null) {
            val thermalRise = afterThermal - beforeThermal
            if (thermalRise >= 4.0) score -= 2 else if (thermalRise <= -3.0) score += 1
        }
        val state = when {
            score >= 3 -> OutcomeState.IMPROVED
            score <= -3 -> OutcomeState.REGRESSED
            else -> OutcomeState.NEUTRAL
        }
        return PolicyOutcome(state, score, "FPS_FRAME_JANK_THERMAL", intent, elapsed)
    }

    private fun updateVerifiedOutcome(snapshot: RuntimeSnapshot) {
        val rb = snapshot.policyReadback
        if (rb.state != PolicyExecutionState.APPLIED) {
            if (rb.state == PolicyExecutionState.FAILED || rb.state == PolicyExecutionState.ROLLED_BACK || rb.state == PolicyExecutionState.SUPPRESSED) {
                outcomeBaseline = null; outcomePolls = 0
                lastOutcome = PolicyOutcome(OutcomeState.INSUFFICIENT_DATA, 0, rb.state.name, rb.intent, 0L)
            }
            return
        }
        val current = outcomeSample(snapshot)
        if (outcomeBaseline == null || outcomeBaselineIntent != rb.intent) {
            outcomeBaseline = current
            outcomeBaselineIntent = rb.intent
            outcomeStartedAt = android.os.SystemClock.elapsedRealtime()
            outcomePolls = 0
            lastOutcome = PolicyOutcome(OutcomeState.PENDING, 0, "OBSERVING", rb.intent, 0L)
            return
        }
        outcomePolls++
        // Five normal HUD polls gives the policy time to settle and avoids judging
        // a one-frame transient. This is outcome feedback, not an actuator loop.
        if (outcomePolls < 5) return
        val elapsed = android.os.SystemClock.elapsedRealtime() - outcomeStartedAt
        lastOutcome = evaluateOutcome(outcomeBaseline!!, current, rb.intent, elapsed)
        outcomeBaseline = current
        outcomeStartedAt = android.os.SystemClock.elapsedRealtime()
        outcomePolls = 0

        // Feedback is typed/read-only from the APK perspective. v12.9.51 does not
        // expose a verified rollback command, so Phase 10 MUST NOT invent one.
        val out = lastOutcome
        val payload = "SCHEMA=DJAEGER_POLICY_OUTCOME_V1 INTENT=${out.intent} OUTCOME=${out.state.name} SCORE=${out.score} OBSERVED_MS=${out.observedMs}"
        thread(name = "djaeger-policy-outcome") {
            runRoot("command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-outcome '$payload' >/dev/null 2>&1 || true")
        }
    }

'''
s = s.replace(parse_anchor, helpers + parse_anchor, 1)

# RuntimeSnapshot is immutable; the persisted outcome is attached at parse time.
old_return = '''            loadSource, policy, policyReadback\n        )\n'''
new_return = '''            loadSource, policy, policyReadback, lastOutcome\n        )\n'''
if old_return not in s:
    raise SystemExit('Build35: phase9 RuntimeSnapshot return anchor missing')
s = s.replace(old_return, new_return, 1)

old_update = '''        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n        dispatchAdaptivePolicy(snapshot)\n'''
new_update = '''        panelSession?.text = "${shortGame(snapshot.game)} • ${snapshot.session.uppercase(Locale.US)}"\n        updateVerifiedOutcome(snapshot)\n        dispatchAdaptivePolicy(snapshot)\n'''
if old_update not in s:
    raise SystemExit('Build35: phase9 update tail missing')
s = s.replace(old_update, new_update, 1)

# Outcome is displayed independently from requested intent and executor state.
old_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_panel = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • ${lastOutcome.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_panel not in s:
    raise SystemExit('Build35: phase9 panelScene anchor missing')
s = s.replace(old_panel, new_panel, 1)
old_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
new_build = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • REQ ${snapshot.policy.intent.name.replace('_', ' ')} • ${snapshot.policyReadback.state.name.replace('_', ' ')} • ${lastOutcome.state.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
if old_build not in s:
    raise SystemExit('Build35: phase9 initial scene text anchor missing')
s = s.replace(old_build, new_build, 1)

required = [
    'OutcomeState { PENDING, IMPROVED, NEUTRAL, REGRESSED, INSUFFICIENT_DATA }',
    'DJAEGER_POLICY_OUTCOME_V1', 'djaeger-ai policy-outcome',
    'outcomePolls < 5', 'FPS_FRAME_JANK_THERMAL',
    'PolicyExecutionState.APPLIED', 'PolicyExecutionState.ROLLED_BACK',
    'djaeger-ai policy-intent-status', 'DJAEGER_LOCAL_POLICY_V1',
    'PROC_STAT+KGSL', 'dumpsys SurfaceFlinger --latency',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build35 regression: required marker missing: {marker}')

# Critical maturity rule: current v12.9.51 has no verified policy rollback API.
# Do not fake rollback via shell/sysfs or guessed djaeger-ai commands.
outcome_body = s.split('private fun updateVerifiedOutcome(snapshot: RuntimeSnapshot)',1)[1].split('private fun parseSnapshot',1)[0]
for forbidden in ('/sys/', 'settings put', 'setprop', 'echo ', 'eval ', 'source ', 'policy-rollback', 'rollback-policy'):
    if forbidden in outcome_body:
        raise SystemExit(f'Build35 authority/rollback regression: {forbidden}')
update_body = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_body:
        raise SystemExit(f'Build35 anti-flicker regression: {forbidden_call}')

h.write_text(s)
print('Build 35 phase 10 applied: verified before/after outcome feedback; rollback intentionally gated until executor API exists')
