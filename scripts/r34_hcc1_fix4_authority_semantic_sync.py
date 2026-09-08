#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

# Semantic synchronization only: make Control Center describe the FIX4 authority
# architecture that the module actually implements.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12238',bs,count=1)
# Keep RC1 as the matched candidate identity; versionCode records this APK rebuild.
b.write_text(bs)

ms=m.read_text()

old_sync='BoxCard("DJAEGER-AI SYNC","Target module: v12.9.50-r3\\nTransport: Gemini v12.9.50 protected baseline\\nControl path: official typed djaeger-ai commands only\\nDisplay/battery cooling: not controlled by Control Center",true)'
new_sync='BoxCard("DJAEGER-AI SYNC","Target module: FIX4 BASELINE RC1 • r92 lineage\\nStrategic path: Gemini-first valid typed policy • Hermes/Local AI fallback\\nHardware path: local typed executor / Root Authority only\\nControl Center path: official typed djaeger-ai commands only",true)'
assert old_sync in ms, 'R34_FAIL=sync-contract-anchor'
ms=ms.replace(old_sync,new_sync,1)

old_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / fallback state reported";else->"State published"};return "Local brain: ${if(s.brain.isBlank())"not published" else "available"}\\nEnvelope: ${if(s.envelope.isBlank())"not published" else "available"}\\nGemini: $gem\\nAuthority: advisory only"}'
new_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / fallback state reported";else->"State published"};val brain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")};val strategic=when(brain){"GEMINI"->"GEMINI • VALID TYPED POLICY";"HERMES_LOCAL"->"HERMES LOCAL";else->if(brain.isBlank())"UNPUBLISHED" else "LOCAL AI • $brain"};return "Local brain: ${if(s.brain.isBlank())"not published" else "available"}\\nEnvelope: ${if(s.envelope.isBlank())"not published" else "available"}\\nGemini: $gem\\nStrategic authority: $strategic\\nHardware authority: LOCAL TYPED EXECUTOR"}'
assert old_summary in ms, 'R34_FAIL=ai-summary-authority-anchor'
ms=ms.replace(old_summary,new_summary,1)

old_monitor='BoxCard("MONITOR INVARIANTS","READ-ONLY application\\nNo direct sysfs writes\\nNo network/game traffic manipulation\\nLocal/native thermal authority preserved\\nGemini remains advisory only")'
new_monitor='BoxCard("MONITOR INVARIANTS","READ-ONLY application\\nNo direct sysfs writes\\nNo network/game traffic manipulation\\nGemini strategic authority requires a fresh validated typed policy\\nHardware writes remain local typed executor only")'
assert old_monitor in ms, 'R34_FAIL=safety-authority-anchor'
ms=ms.replace(old_monitor,new_monitor,1)

old_restore='BoxCard("RESTORATION WATCH","Control Center does not alter CPU/GPU state. Original-state restoration remains owned by DJAEGER controller lifecycle and its fail-safe paths.")'
new_restore='BoxCard("RESTORATION WATCH","Control Center does not alter CPU/GPU state. Original-state restoration is owned by DJAEGER Root Authority with session/boot validation, bounded retry, and hardware readback.")'
assert old_restore in ms, 'R34_FAIL=restore-authority-anchor'
ms=ms.replace(old_restore,new_restore,1)

m.write_text(ms)

M=m.read_text(); B=b.read_text()
assert 'versionCode = 12238' in B
for old in ['Target module: v12.9.50-r3','Gemini remains advisory only','Authority: advisory only','restoration remains owned by DJAEGER controller lifecycle']:
    assert old not in M, old
for new in ['Target module: FIX4 BASELINE RC1 • r92 lineage','Gemini strategic authority requires a fresh validated typed policy','Hardware writes remain local typed executor only','Original-state restoration is owned by DJAEGER Root Authority','Hardware authority: LOCAL TYPED EXECUTOR']:
    assert new in M, new
# Preserve RC1 freshness and HCC1 contracts.
assert 'private fun runtimeStateStale(' in M
assert 'jankText(s.telemetry.jank)' in M
assert 'HumanComfortHcc1Card(s);' in M
assert 'TELEMETRI 1 DETIK' in M
print('FIX4_RC1_AUTHORITY_SEMANTICS=PASS')
print('FIX4_RC1_GEMINI_STRATEGIC_TYPED_POLICY=PASS')
print('FIX4_RC1_HARDWARE_LOCAL_TYPED_EXECUTOR=PASS')
print('FIX4_RC1_RESTORE_ROOT_AUTHORITY=PASS')
print('FIX4_RC1_FRESHNESS_HCC1_PRESERVED=PASS')
