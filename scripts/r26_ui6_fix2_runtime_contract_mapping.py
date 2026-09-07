#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

# UI6 FIX2 is a surgical runtime-contract repair on top of UI6 FIX1.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12229',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2"',bs,count=1)
b.write_text(bs)

# Root cause: r20 added RuntimeState.authority/sessionSafety/supervisor and the UI cards,
# but the later consolidated cc_snapshot path never mapped AUTHORITY/SESSION_SAFETY/
# SUPERVISOR into ConsolidatedRuntimeMapper. Therefore those RuntimeState fields stayed
# empty even though the module published the sections.
cs=mapper.read_text()
if 'val authority: String,' not in cs:
    anchor='        val memoryStatus: String,\n'
    assert anchor in cs, 'UI6_FIX2_FAIL=mapper-field-anchor'
    cs=cs.replace(anchor,anchor+'        val authority: String,\n        val sessionSafety: String,\n        val supervisor: String,\n',1)
if 'authority = s["AUTHORITY"].orEmpty(),' not in cs:
    anchor='            memoryStatus = s["MEMORY"].orEmpty(),\n'
    assert anchor in cs, 'UI6_FIX2_FAIL=mapper-map-anchor'
    cs=cs.replace(anchor,anchor+'            authority = s["AUTHORITY"].orEmpty(),\n            sessionSafety = s["SESSION_SAFETY"].orEmpty(),\n            supervisor = s["SUPERVISOR"].orEmpty(),\n',1)
mapper.write_text(cs)

rs=r.read_text()
for required in ['val authority:String=""','val sessionSafety:String=""','val supervisor:String=""']:
    assert required in rs, 'UI6_FIX2_FAIL=runtime-state-'+required
if 'authority=mapped.authority' not in rs:
    # r22 UI2 placed strategyResult on the same line as memoryStatus. Insert after
    # the complete memory/strategy expression rather than assuming old formatting.
    anchor='memoryStatus=mapped.memoryStatus,strategyResult=mapped.strategyResult,'
    if anchor in rs:
        rs=rs.replace(anchor,anchor+'authority=mapped.authority,sessionSafety=mapped.sessionSafety,supervisor=mapped.supervisor,',1)
    else:
        anchor='memoryStatus=mapped.memoryStatus,'
        assert anchor in rs, 'UI6_FIX2_FAIL=repository-map-anchor'
        rs=rs.replace(anchor,anchor+'authority=mapped.authority,sessionSafety=mapped.sessionSafety,supervisor=mapped.supervisor,',1)

# Preserve the single atomic recurring read. Do not re-introduce direct root/file reads.
start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=rs.index('    suspend fun setUserMode',start)
snap=rs[start:end]
for required in ['ConsolidatedSnapshotReader','authority=mapped.authority','sessionSafety=mapped.sessionSafety','supervisor=mapped.supervisor']:
    assert required in snap, 'UI6_FIX2_FAIL=snapshot-'+required
for forbidden in ['/sys/','authority_state.env','session_safety.env','session_recovery_state','snapshot_lifecycle.log']:
    assert forbidden not in snap, 'UI6_FIX2_FAIL=direct-read-'+forbidden
r.write_text(rs)

ms=m.read_text()
old='CONTROL CENTER • v0.12.1-r22-r92ui6-fix1 • HERMES H2 RT3 FIX1'
new='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2 • HERMES H2 RT3 FIX2'
assert old in ms, 'UI6_FIX2_FAIL=header-anchor'
ms=ms.replace(old,new,1)

# UI6 presentation remains exactly the same; only the previously-empty data path is wired.
assert 'BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)' in ms
assert 'BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)' in ms
assert 'StatusCard(s);ThoughtsCard(s);HermesCard(s);StrategyCard(s);OutcomeLearningCard(s);' in ms
assert 'Cloud active:' not in ms
assert 'Gemini: $geminiLine' in ms
for forbidden in ['/sys/','iptables','ip6tables','settings put','setprop','force-stop','ProcessBuilder']:
    assert forbidden not in ms, forbidden
m.write_text(ms)

# Final contract gates.
cs=mapper.read_text(); rs=r.read_text()
for required in [
    'val authority: String,','val sessionSafety: String,','val supervisor: String,',
    'authority = s["AUTHORITY"].orEmpty(),','sessionSafety = s["SESSION_SAFETY"].orEmpty(),','supervisor = s["SUPERVISOR"].orEmpty(),'
]: assert required in cs, required
for required in ['authority=mapped.authority','sessionSafety=mapped.sessionSafety','supervisor=mapped.supervisor']:
    assert required in rs, required

print('UI6_FIX2_BASELINE=UI6_FIX1_COMMIT_7588d85')
print('UI6_FIX2_ROOT_CAUSE=R20_FIELDS_NOT_WIRED_TO_CONSOLIDATED_MAPPER')
print('UI6_FIX2_AUTHORITY_MAPPING=PASS')
print('UI6_FIX2_SESSION_SAFETY_MAPPING=PASS')
print('UI6_FIX2_SUPERVISOR_MAPPING=PASS')
print('UI6_FIX2_LAYOUT_CHANGE=NONE')
print('UI6_FIX2_ROOT_READ_CHANGE=NONE')
print('UI6_FIX2_GEMINI_HERMES_AUTHORITY_CHANGE=NONE')
