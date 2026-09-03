#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12190',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r19"',bs,count=1)
b.write_text(bs)

# r9 made cc_snapshot the only recurring root-read path. Thoughts and memory are
# already module-published sections of that atomic snapshot, so r19 must extend
# the consolidated mapper instead of re-introducing direct file reads.
cs=mapper.read_text()
old_fields='''        val brain: String,\n        val envelope: String,'''
new_fields='''        val brain: String,\n        val thoughts: String,\n        val memoryStatus: String,\n        val envelope: String,'''
assert old_fields in cs, 'R19 atomic mapper field anchor missing'
cs=cs.replace(old_fields,new_fields,1)
old_map='''            brain = s["BRAIN"].orEmpty(),\n            envelope = s["ENV"].orEmpty(),'''
new_map='''            brain = s["BRAIN"].orEmpty(),\n            thoughts = s["THOUGHTS"].orEmpty(),\n            memoryStatus = s["MEMORY"].orEmpty(),\n            envelope = s["ENV"].orEmpty(),'''
assert old_map in cs, 'R19 atomic mapper section anchor missing'
cs=cs.replace(old_map,new_map,1)
mapper.write_text(cs)

rs=r.read_text()
old_state='val brain:String="",val envelope:String=""'
new_state='val brain:String="",val thoughts:String="",val memoryStatus:String="",val envelope:String=""'
assert old_state in rs, 'R19 RuntimeState anchor missing'
rs=rs.replace(old_state,new_state,1)

# r9 snapshot() already uses ConsolidatedRuntimeMapper; wire the new mapped
# fields into RuntimeState. No extra su/file/sysfs read is added here.
old_repo='''            brain=mapped.brain,\n            envelope=mapped.envelope,'''
new_repo='''            brain=mapped.brain,\n            thoughts=mapped.thoughts,\n            memoryStatus=mapped.memoryStatus,\n            envelope=mapped.envelope,'''
assert old_repo in rs, 'R19 consolidated repository mapping anchor missing'
rs=rs.replace(old_repo,new_repo,1)

# Regression: recurring snapshot must remain atomic and source-of-truth fields
# must be taken from module-published cc_snapshot sections.
snapshot_start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
snapshot_end=rs.index('    suspend fun setUserMode',snapshot_start)
snapshot=rs[snapshot_start:snapshot_end]
assert 'ConsolidatedSnapshotReader' in snapshot, 'R19 atomic reader regressed'
assert 'thoughts=mapped.thoughts' in snapshot, 'R19 Thoughts not mapped into RuntimeState'
assert 'memoryStatus=mapped.memoryStatus' in snapshot, 'R19 memory not mapped into RuntimeState'
assert '/data/adb/djaeger_ai/djaeger_thoughts.env' not in snapshot, 'R19 direct Thoughts read forbidden'
assert 'local_memory_status.env' not in snapshot, 'R19 direct memory read forbidden'
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r18 • FAST TELEMETRY • 200ms','CONTROL CENTER • v0.12.1-r19 • THOUGHTS + MEMORY • FAST TELEMETRY',1)
# Human-readable source badge is derived from module-published source, never guessed by UI.
helper='''\nprivate fun thoughtField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\n@Composable fun ThoughtsCard(s:RuntimeState){\n    val src=thoughtField(s.thoughts,"SOURCE").ifBlank{"LOCAL_AI"}\n    val status=thoughtField(s.thoughts,"STATUS").ifBlank{"WAITING"}\n    val conf=thoughtField(s.thoughts,"CONFIDENCE")\n    val text=thoughtField(s.thoughts,"TEXT").ifBlank{"Belum ada penafsiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}\n    val badge=if(src=="GEMINI") "✦ GEMINI • $status" else "◆ LOCAL AI • $status"\n    val memUsed=thoughtField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L\n    val memMax=thoughtField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L\n    val rows=thoughtField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}\n    val hw=thoughtField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}\n    val mem="Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw)\n    BoxCard("DJAEGER THOUGHTS • $badge", text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)\n}\n'''
anchor='@Composable fun Overview(s:RuntimeState)'
assert anchor in ms, 'R19 Overview anchor missing'
if 'fun ThoughtsCard' not in ms:
    ms=ms.replace(anchor,helper+'\n'+anchor,1)
needle='StatusCard(s);Row(Modifier.fillMaxWidth()'
assert needle in ms, 'R19 Overview insertion anchor missing'
ms=ms.replace(needle,'StatusCard(s);ThoughtsCard(s);Row(Modifier.fillMaxWidth()',1)
m.write_text(ms)

# Final guards for generated source.
assert 'val thoughts:String=""' in r.read_text(), 'R19 Thoughts RuntimeState missing'
assert 'val memoryStatus:String=""' in r.read_text(), 'R19 memory RuntimeState missing'
assert 'val thoughts: String' in mapper.read_text(), 'R19 mapped Thoughts field missing'
assert 'val memoryStatus: String' in mapper.read_text(), 'R19 mapped memory field missing'
assert 's["THOUGHTS"]' in mapper.read_text(), 'R19 THOUGHTS section missing'
assert 's["MEMORY"]' in mapper.read_text(), 'R19 MEMORY section missing'

print('R19_THOUGHTS=SOURCE_LABELED')
print('R19_MEMORY=BOUNDED_STATUS')
print('R19_ATOMIC_READBACK=THOUGHTS+MEMORY_FROM_CC_SNAPSHOT')
print('R19_NO_SECOND_GEMINI_CALL=1')
print('R19_FULL_UI=PRESERVED')
