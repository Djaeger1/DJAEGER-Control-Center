from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 36', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.12.0-rc-stage12-maturity"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.9 RC • VERIFIED OUTCOME PHASE 10 • REALTIME 1s',
                'GAMING TURBO • v0.12.0 RC • STAGE 12 MATURITY • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.9 RC', 'DJAEGER v0.12.0 RC')
m.write_text(ms)

# Phase 10 referenced snapshot.jank but RuntimeSnapshot did not carry jank.
# Add it explicitly and keep positional construction deterministic.
old_runtime_head = '''        val fps: String = "--",\n        val frameMs: String = "--",\n        val cpuTemp: String = "--",\n'''
new_runtime_head = '''        val fps: String = "--",\n        val frameMs: String = "--",\n        val jank: String = "--",\n        val cpuTemp: String = "--",\n'''
if old_runtime_head not in s:
    raise SystemExit('Build36: RuntimeSnapshot head anchor missing')
s = s.replace(old_runtime_head, new_runtime_head, 1)

old_return_head = '''            one(fps), one(frame), temp(cpu), temp(gpu), mode.uppercase(Locale.US),\n'''
new_return_head = '''            one(fps), one(frame), one(jank), temp(cpu), temp(gpu), mode.uppercase(Locale.US),\n'''
if old_return_head not in s:
    raise SystemExit('Build36: RuntimeSnapshot constructor head anchor missing')
s = s.replace(old_return_head, new_return_head, 1)

# Replace the post-APPLIED baseline model with an immutable PRE-DISPATCH baseline.
old_state = '''    private var outcomeBaseline: OutcomeSample? = null\n    private var outcomeBaselineIntent = "NONE"\n    private var outcomeStartedAt = 0L\n    private var outcomePolls = 0\n    private var lastOutcome = PolicyOutcome()\n'''
new_state = '''    private var outcomeBaseline: OutcomeSample? = null\n    private var outcomeBaselineIntent = "NONE"\n    private var outcomeBaselineDispatchAt = 0L\n    private var outcomeStartedAt = 0L\n    private var outcomePolls = 0\n    private var lastOutcome = PolicyOutcome()\n'''
if old_state not in s:
    raise SystemExit('Build36: Phase10 outcome state anchor missing')
s = s.replace(old_state, new_state, 1)

# Arm baseline immediately before policy dispatch. This makes before/after real:
# BEFORE = telemetry that caused the intent; AFTER = telemetry after executor APPLIED.
parse_anchor = '    private fun parseSnapshot(raw: String): RuntimeSnapshot {\n'
if parse_anchor not in s:
    raise SystemExit('Build36: parseSnapshot anchor missing')
arm_helper = r'''    private fun armOutcomeBaseline(snapshot: RuntimeSnapshot, intent: String, dispatchAt: Long) {
        outcomeBaseline = outcomeSample(snapshot)
        outcomeBaselineIntent = intent
        outcomeBaselineDispatchAt = dispatchAt
        outcomeStartedAt = 0L
        outcomePolls = 0
        lastOutcome = PolicyOutcome(OutcomeState.PENDING, 0, "PRE_DISPATCH_BASELINE", intent, 0L)
    }

'''
s = s.replace(parse_anchor, arm_helper + parse_anchor, 1)

# Arm baseline only after hysteresis/cooldown gates passed and immediately before
# request leaves the APK. A suppressed or failed request will clear it on readback.
old_dispatch_marker = '''        lastPolicyDispatchAt = now\n        lastPolicyIntent = policy.intent\n        thread(name = "djaeger-local-policy") {\n'''
new_dispatch_marker = '''        armOutcomeBaseline(snapshot, intent, now)\n        lastPolicyDispatchAt = now\n        lastPolicyIntent = policy.intent\n        thread(name = "djaeger-local-policy") {\n'''
if old_dispatch_marker not in s:
    raise SystemExit('Build36: dispatch marker missing')
s = s.replace(old_dispatch_marker, new_dispatch_marker, 1)

# Replace Phase10 outcome evaluator lifecycle. It must never create baseline after
# APPLIED; it only consumes a baseline captured before dispatch.
start = s.find('    private fun updateVerifiedOutcome(snapshot: RuntimeSnapshot) {')
end = s.find('\n    private fun armOutcomeBaseline(', start)
if start < 0 or end < 0:
    raise SystemExit('Build36: updateVerifiedOutcome boundaries missing')
new_update = r'''    private fun updateVerifiedOutcome(snapshot: RuntimeSnapshot) {
        val rb = snapshot.policyReadback
        if (rb.state != PolicyExecutionState.APPLIED) {
            if (rb.state == PolicyExecutionState.FAILED ||
                rb.state == PolicyExecutionState.ROLLED_BACK ||
                rb.state == PolicyExecutionState.SUPPRESSED ||
                rb.state == PolicyExecutionState.UNAVAILABLE) {
                outcomeBaseline = null
                outcomeBaselineIntent = "NONE"
                outcomeBaselineDispatchAt = 0L
                outcomeStartedAt = 0L
                outcomePolls = 0
                lastOutcome = PolicyOutcome(OutcomeState.INSUFFICIENT_DATA, 0, rb.state.name, rb.intent, 0L)
            }
            return
        }

        val baseline = outcomeBaseline ?: run {
            lastOutcome = PolicyOutcome(OutcomeState.INSUFFICIENT_DATA, 0, "PRE_DISPATCH_BASELINE_MISSING", rb.intent, 0L)
            return
        }
        if (outcomeBaselineIntent != rb.intent) {
            lastOutcome = PolicyOutcome(OutcomeState.INSUFFICIENT_DATA, 0, "INTENT_BASELINE_MISMATCH", rb.intent, 0L)
            return
        }

        if (outcomeStartedAt == 0L) {
            outcomeStartedAt = android.os.SystemClock.elapsedRealtime()
            outcomePolls = 0
            lastOutcome = PolicyOutcome(OutcomeState.PENDING, 0, "POST_APPLY_OBSERVING", rb.intent, 0L)
            return
        }

        outcomePolls++
        if (outcomePolls < 5) return
        val now = android.os.SystemClock.elapsedRealtime()
        val elapsed = now - outcomeStartedAt
        val current = outcomeSample(snapshot)
        lastOutcome = evaluateOutcome(baseline, current, rb.intent, elapsed)

        // Consume this transaction baseline exactly once. A fresh policy dispatch
        // must arm a fresh baseline; repeated APPLIED polls cannot self-compare.
        outcomeBaseline = null
        outcomeBaselineIntent = "NONE"
        outcomeBaselineDispatchAt = 0L
        outcomeStartedAt = 0L
        outcomePolls = 0

        val out = lastOutcome
        val payload = "SCHEMA=DJAEGER_POLICY_OUTCOME_V1 INTENT=${out.intent} OUTCOME=${out.state.name} SCORE=${out.score} OBSERVED_MS=${out.observedMs}"
        thread(name = "djaeger-policy-outcome") {
            runRoot("command -v djaeger-ai >/dev/null 2>&1 && djaeger-ai policy-outcome '$payload' >/dev/null 2>&1 || true")
        }
    }
'''
s = s[:start] + new_update + s[end:]

required = [
    'val jank: String = "--"',
    'one(fps), one(frame), one(jank)',
    'PRE_DISPATCH_BASELINE', 'POST_APPLY_OBSERVING',
    'PRE_DISPATCH_BASELINE_MISSING', 'INTENT_BASELINE_MISMATCH',
    'armOutcomeBaseline(snapshot, intent, now)',
    'outcomePolls < 5', 'DJAEGER_POLICY_OUTCOME_V1', 'djaeger-ai policy-outcome',
    'PolicyExecutionState.ROLLED_BACK', 'PolicyExecutionState.SUPPRESSED',
    'djaeger-ai policy-intent-status', 'DJAEGER_LOCAL_POLICY_V1',
    'PROC_STAT+KGSL', 'dumpsys SurfaceFlinger --latency',
    'readFreeformState(pkg)',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build36 regression: required marker missing: {marker}')

# Maturity invariants.
if 'snapshot.jank.toDoubleOrNull()' not in s:
    raise SystemExit('Build36: outcome jank source not wired')
update_outcome = s.split('private fun updateVerifiedOutcome(snapshot: RuntimeSnapshot)',1)[1].split('private fun armOutcomeBaseline',1)[0]
if 'outcomeBaseline = current' in update_outcome:
    raise SystemExit('Build36: post-APPLIED baseline regression remains')
if 'outcomeBaseline = outcomeSample(snapshot)' in update_outcome:
    raise SystemExit('Build36: baseline may not be created in post-APPLIED path')
policy_body = s.split('private fun dispatchAdaptivePolicy(snapshot: RuntimeSnapshot)',1)[1].split('private fun outcomeSample',1)[0]
if policy_body.find('armOutcomeBaseline(snapshot, intent, now)') > policy_body.find('thread(name = "djaeger-local-policy")'):
    raise SystemExit('Build36: baseline is not armed before dispatch')
for forbidden in ('/sys/', 'settings put', 'setprop', 'eval ', 'source ', 'policy-rollback', 'rollback-policy'):
    if forbidden in update_outcome:
        raise SystemExit(f'Build36 authority regression: {forbidden}')
update_ui = s.split('private fun updateOverlayContent()',1)[1].split('private fun buildHandle()',1)[0]
for forbidden_call in ('removeView', 'addView', 'showOverlay', 'rebuildOverlayKeepingPosition'):
    if forbidden_call in update_ui:
        raise SystemExit(f'Build36 anti-flicker regression: {forbidden_call}')

h.write_text(s)
print('Build 36 Stage 12 maturity fix applied: jank field + immutable pre-dispatch baseline + single-consume outcome transaction')
