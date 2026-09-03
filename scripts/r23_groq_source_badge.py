#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • GEMINI + GROQ SOURCE',1).replace('v0.12.1-r22','v0.12.1-r23')
old='val badge=when(src){"GEMINI"->"✦ GEMINI • $status";"LOCAL_AI"->"◆ LOCAL AI • $status";else->"-"}'
new='val badge=when(src){"GEMINI"->"✦ GEMINI • $status";"GROQ"->"◇ GROQ • $status";"LOCAL_AI"->"◆ LOCAL AI • $status";else->"-"}'
assert old in ms, 'R23 Groq source badge anchor missing'
ms=ms.replace(old,new,1)
assert '"GROQ"->"◇ GROQ • $status"' in ms, 'R23 Groq badge missing'
assert 'thoughtField(s.thoughts,"SOURCE")' in ms, 'R23 must remain backend SOURCE driven'
assert 'geminiHttp.contains("LAST_HTTP_CODE=200")' not in ms, 'R23 must never infer reasoner from transport status'
m.write_text(ms)

print('R23_GROQ_SOURCE_BADGE=PASS')
print('R23_SOURCE_OF_TRUTH=MODULE_PUBLISHED_THOUGHTS')
print('R23_NO_EXTRA_ROOT_READS=1')
print('R23_BACKEND_EXECUTOR_AUTHORITY=UNCHANGED')
