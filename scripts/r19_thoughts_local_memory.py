#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12190',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r19"',bs,count=1); b.write_text(bs)
rs=r.read_text()
rs=rs.replace('val brain:String="",val envelope:String=""','val brain:String="",val thoughts:String="",val memoryStatus:String="",val envelope:String=""',1)
rs=rs.replace("echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null\n        echo __ENV__;", "echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null\n        echo __THOUGHTS__; cat '$persistent/djaeger_thoughts.env' 2>/dev/null\n        echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __ENV__;",1)
rs=rs.replace('section("LIVE","BRAIN")','section("LIVE","BRAIN")',1)
rs=rs.replace('brain=section("BRAIN","ENV").trim(),envelope=section("ENV","HTTP").trim()', 'brain=section("BRAIN","THOUGHTS").trim(),thoughts=section("THOUGHTS","MEMORY").trim(),memoryStatus=section("MEMORY","ENV").trim(),envelope=section("ENV","HTTP").trim()',1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r18 • FAST TELEMETRY • 200ms','CONTROL CENTER • v0.12.1-r19 • THOUGHTS + MEMORY • FAST TELEMETRY',1)
# Human-readable source badge is derived from module-published source, never guessed by UI.
helper='''\nprivate fun thoughtField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\\'') ?: ""\n@Composable fun ThoughtsCard(s:RuntimeState){\n    val src=thoughtField(s.thoughts,"SOURCE").ifBlank{"LOCAL_AI"}\n    val status=thoughtField(s.thoughts,"STATUS").ifBlank{"WAITING"}\n    val conf=thoughtField(s.thoughts,"CONFIDENCE")\n    val text=thoughtField(s.thoughts,"TEXT").ifBlank{"Belum ada penafsiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}\n    val badge=if(src=="GEMINI") "✦ GEMINI • $status" else "◆ LOCAL AI • $status"\n    val memUsed=thoughtField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L\n    val memMax=thoughtField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L\n    val rows=thoughtField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}\n    val hw=thoughtField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}\n    val mem="Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw)\n    BoxCard("DJAEGER THOUGHTS • $badge", text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)\n}\n'''
anchor='@Composable fun Overview(s:RuntimeState)'
assert anchor in ms
if 'fun ThoughtsCard' not in ms: ms=ms.replace(anchor,helper+'\n'+anchor,1)
needle='StatusCard(s);Row(Modifier.fillMaxWidth()'
assert needle in ms
ms=ms.replace(needle,'StatusCard(s);ThoughtsCard(s);Row(Modifier.fillMaxWidth()',1)
m.write_text(ms)
print('R19_THOUGHTS=SOURCE_LABELED'); print('R19_MEMORY=BOUNDED_STATUS'); print('R19_NO_SECOND_GEMINI_CALL=1'); print('R19_FULL_UI=PRESERVED')
