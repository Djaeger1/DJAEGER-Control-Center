from pathlib import Path

h = Path('app/src/main/java/com/djaeger/controlcenter/DjaegerHudService.kt')
s = h.read_text()

phase5_update = '''        panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"'''
phase7_update = '''        panelScene?.text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''
phase5_initial = '''            text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}%"'''
phase7_initial = '''            text = "${snapshot.scene.state.name.replace('_', ' ')} • ${snapshot.scene.confidence}% • ${snapshot.policy.intent.name.replace('_', ' ')} • C ${snapshot.cpuLoad}% G ${snapshot.gpuLoad}%"'''

if phase7_update not in s:
    if phase5_update not in s:
        raise SystemExit('Build33c: Phase5 update scene text missing')
    s = s.replace(phase5_update, phase7_update, 1)
if phase7_initial not in s:
    if phase5_initial not in s:
        raise SystemExit('Build33c: Phase5 initial scene text missing')
    s = s.replace(phase5_initial, phase7_initial, 1)

if phase7_update not in s or phase7_initial not in s:
    raise SystemExit('Build33c: policy HUD reconciliation incomplete')
for marker in (
    'DJAEGER_LOCAL_POLICY_V1', 'djaeger-ai policy-intent',
    'snapshot.policy.intent.name', 'snapshot.cpuLoad', 'snapshot.gpuLoad',
    'private fun updateOverlayContent()'
):
    if marker not in s:
        raise SystemExit(f'Build33c regression: {marker}')

h.write_text(s)
print('Build 33c Stage12 policy HUD reconciliation applied with exact update/initial anchors')
