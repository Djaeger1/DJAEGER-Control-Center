#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12220',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22"',bs,count=1); b.write_text(bs)
rs=r.read_text(); r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r21 • RUNTIME BUGFIX','CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS',1).replace('v0.12.1-r21','v0.12.1-r22')
# Preserve module-published source. If source is absent only, prefer Gemini after successful transport.
ms=re.sub(r'val src=thoughtField\(s\.thoughts,"SOURCE"\)\.ifBlank\s*\{\s*"LOCAL_AI"\s*\}', 'val src=thoughtField(s.thoughts,"SOURCE").ifBlank{if(s.geminiHttp.contains("LAST_HTTP_CODE=200")) "GEMINI" else "LOCAL_AI"}', ms, count=1)
# Missing memory contract is unavailable, not a genuine zero-capacity store.
ms=ms.replace('val mem="Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw)', 'val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"',1)
m.write_text(ms)
print('R22_THOUGHTS_PRIORITY=GEMINI_VALID_FIRST_LOCAL_AI_FALLBACK')
print('R22_MEMORY=NO_FALSE_0_MIB')
print('R22_EXECUTOR_AUTHORITY=UNCHANGED_LOCAL_VALIDATION_REQUIRED')
