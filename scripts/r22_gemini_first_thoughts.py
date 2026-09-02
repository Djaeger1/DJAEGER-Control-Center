#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12220',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r19 already introduced first-class THOUGHTS and MEMORY sections. Keep that contract intact.
assert 'djaeger_thoughts.env' in rs and 'local_memory_status.env' in rs
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r21 • RUNTIME BUGFIX','CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS',1)
# Gemini-first display policy: when the latest transport is HTTP 200 and the module has not yet
# refreshed the Thoughts publisher, present Gemini as the preferred planner. Once the publisher
# explicitly says GEMINI or LOCAL_AI, that source remains authoritative.
old='val src=thoughtField(s.thoughts,"SOURCE").ifBlank{"LOCAL_AI"}'
new='val src=thoughtField(s.thoughts,"SOURCE").ifBlank{if(s.geminiHttp.contains("LAST_HTTP_CODE=200")) "GEMINI" else "LOCAL_AI"}'
assert old in ms; ms=ms.replace(old,new,1)
# Do not lie about empty memory capacity: distinguish unavailable contract from real zero usage.
old2='val mem="Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw)'
new2='val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"'
assert old2 in ms; ms=ms.replace(old2,new2,1)
m.write_text(ms)
print('R22_THOUGHTS_PRIORITY=GEMINI_VALID_FIRST_LOCAL_AI_FALLBACK')
print('R22_MEMORY=NO_FALSE_0_MIB')
print('R22_EXECUTOR_AUTHORITY=UNCHANGED_LOCAL_VALIDATION_REQUIRED')
