#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12220',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Always publish first-class Thoughts + Memory sections from the persistent runtime contract.
rs=rs.replace("echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null", "echo __THOUGHTS__; cat '$persistent/djaeger_thoughts.env' 2>/dev/null\n        echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null",1)
# Add fields without changing executor authority.
rs=rs.replace('val brain:String="",val envelope:String=""','val thoughts:String="",val memoryStatus:String="",val brain:String="",val envelope:String=""',1)
rs=rs.replace('brain=section("BRAIN","ENV").trim()', 'thoughts=section("THOUGHTS","MEMORY").trim(),memoryStatus=section("MEMORY","BRAIN").trim(),brain=section("BRAIN","ENV").trim()',1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r21 • RUNTIME BUGFIX','CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS',1)
# Replace the old Thoughts presentation logic if present: runtime SOURCE is authoritative.
# Gemini source is displayed first whenever publisher marks it valid; Local AI is fallback only.
old='''val thoughtSource = parseEnv(s.thoughts,"SOURCE").ifBlank { "LOCAL_AI" }'''
new='''val thoughtSource = parseEnv(s.thoughts,"SOURCE").ifBlank { if(s.geminiHttp.contains("LAST_HTTP_CODE=200")) "GEMINI" else "LOCAL_AI" }'''
if old in ms: ms=ms.replace(old,new,1)
# Header/version fallback for variants.
ms=ms.replace('v0.12.1-r21','v0.12.1-r22')
m.write_text(ms)
print('R22_THOUGHTS_PRIORITY=GEMINI_VALID_FIRST_LOCAL_AI_FALLBACK')
print('R22_MEMORY=FIRST_CLASS_RUNTIME_CONTRACT')
print('R22_EXECUTOR_AUTHORITY=UNCHANGED_LOCAL_VALIDATION_REQUIRED')
