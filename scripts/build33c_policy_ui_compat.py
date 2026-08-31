from pathlib import Path

h = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = h.read_text()

phase5_update = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"'''
phase7_update = '''panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
phase5_initial = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"'''
phase7_initial = '''text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''

# Original Build33's UI replacement is intentionally non-failing; with the
# Stage12 Build32b source it can remain at the Phase5 string. Reconcile it here.
if phase7_update not in s:
    if phase5_update not in s:
        raise SystemExit('Build33c: neither Phase5 nor Phase7 update scene text found')
    s = s.replace(phase5_update, phase7_update, 1)
if phase7_initial not in s:
    if phase5_initial not in s:
        raise SystemExit('Build33c: neither Phase5 nor Phase7 initial scene text found')
    s = s.replace(phase5_initial, phase7_initial, 1)

for marker in (
    'DJAEGER_LOCAL_POLICY_V1', 'djaeger-ai policy-intent',
    'snapshot.policy.intent.name', 'snapshot.cpuLoad', 'snapshot.gpuLoad',
    'private fun updateOverlayContent()'
):
    if marker not in s:
        raise SystemExit(f'Build33c regression: {marker}')

h.write_text(s)
print('Build 33c Stage12 policy HUD reconciliation applied')
