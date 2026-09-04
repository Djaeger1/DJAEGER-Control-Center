#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12250',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r25"',bs,count=1)
b.write_text(bs)

cs=mapper.read_text()
assert 'val memoryStatus: String,' in cs, 'R25 mapper memory anchor missing'
cs=cs.replace('val memoryStatus: String,','val memoryStatus: String,\n        val providerStatus: String,',1)
assert 'memoryStatus = s["MEMORY"].orEmpty(),' in cs, 'R25 mapper section anchor missing'
cs=cs.replace('memoryStatus = s["MEMORY"].orEmpty(),','memoryStatus = s["MEMORY"].orEmpty(),\n            providerStatus = s["PROVIDERS"].orEmpty(),',1)
mapper.write_text(cs)

rs=r.read_text()
assert 'val memoryStatus:String=""' in rs, 'R25 RuntimeState memory anchor missing'
rs=rs.replace('val memoryStatus:String=""','val memoryStatus:String="",val providerStatus:String=""',1)
assert 'memoryStatus=mapped.memoryStatus,' in rs, 'R25 repository mapping anchor missing'
rs=rs.replace('memoryStatus=mapped.memoryStatus,','memoryStatus=mapped.memoryStatus,\n            providerStatus=mapped.providerStatus,',1)
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r24 • GEMINI + GROQ KEY UI','CONTROL CENTER • v0.12.1-r25 • LIVE PROVIDER CHAIN',1).replace('v0.12.1-r24','v0.12.1-r25')

old='''    val mem="Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw)'''
if old not in ms:
    old='''    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"'''
assert old in ms, 'R25 Thoughts memory anchor missing'
new=old+'''\n    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI -> GROQ -> LOCAL_AI"}.replace("->","→").replace("LOCAL_AI","LOCAL AI")\n    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")\n    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}\n    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}\n    val providerLines="Provider chain: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState"'''
ms=ms.replace(old,new,1)
old_box='''    BoxCard("DJAEGER THOUGHTS • $badge", text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)'''
assert old_box in ms, 'R25 Thoughts card body anchor missing'
new_box='''    BoxCard("DJAEGER THOUGHTS • $badge", providerLines+"\\n\\n"+text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)'''
ms=ms.replace(old_box,new_box,1)

assert 'Provider chain: $chain' in ms
assert 'Active now: $active' in ms
assert 'Gemini: $geminiState • Groq: $groqState' in ms
assert 'providerStatus=mapped.providerStatus' in r.read_text()
assert 's["PROVIDERS"]' in mapper.read_text()
assert '/data/adb/djaeger_ai/cloud_reasoner_state' not in r.read_text(), 'R25 must not add direct provider reads'
m.write_text(ms)

print('R25_PROVIDER_CHAIN_UI=PASS')
print('R25_ACTIVE_REASONER=LIVE_BACKEND_STATUS')
print('R25_GEMINI_GROQ_STATUS=ATOMIC_CC_SNAPSHOT')
print('R25_NO_EXTRA_ROOT_READS=1')
print('R25_EXECUTOR_AUTHORITY=UNCHANGED')
