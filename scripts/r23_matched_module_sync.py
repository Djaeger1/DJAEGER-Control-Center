#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r115 publishes one atomic app-facing truth file. Read it in the same root snapshot as telemetry.
needle="        echo __BRAIN__;"
assert needle in rs
rs=rs.replace(needle,"        echo __CCSYNC__; cat '$persistent/cc_sync.env' 2>/dev/null\n"+needle,1)
# Do not let CCSYNC lines pollute direct live sysfs parsing.
rs=rs.replace('section("LIVE","BRAIN")','section("LIVE","CCSYNC")')
# Parse canonical contract once; prefer it over legacy runtime_status aliases.
anchor='        fun maxTemp(test:(String)->Boolean):Int=TelemetryNormalizer.maxThermal(thermals,test)'
assert anchor in rs
rs=rs.replace(anchor,'        val sync=section("CCSYNC","BRAIN").lineSequence().mapNotNull{line-> val p=line.indexOf(\'=\'); if(p<=0)null else line.substring(0,p).trim() to line.substring(p+1).trim().trim().trim(\'\\\'\')}.toMap()\n'+anchor,1)
# Strategy cards consume canonical r115 contract first, with old runtime_status only as compatibility fallback.
old='fun rv(vararg k:String):String{k.forEach{if(!rt[it].isNullOrBlank())return rt[it]!!};return "—"}'
new='fun rv(vararg k:String):String{k.forEach{key->sync[key]?.takeIf{it.isNotBlank()&&it!="NA"}?.let{return it};rt[key]?.takeIf{it.isNotBlank()&&it!="NA"}?.let{return it}};return "—"}'
assert old in rs
rs=rs.replace(old,new,1)
# Profile shown by Performance follows the same canonical execution contract.
old='val tel=csv.copy('
assert old in rs
rs=rs.replace(old,'val tel=csv.copy(\n            profile=sync["PROFILE"]?.takeIf{it.isNotBlank()&&it!="NA"}?:csv.profile,',1)
r.write_text(rs)
ms=m.read_text()
# User requested these internal-only panels removed from the app. Internal backend safety remains intact.
ms=re.sub(r'\s*BoxCard\("KERNEL AUTHORITY",s\.authority\.ifBlank\{"UNAVAILABLE — authority state not published\."\},true\)','',ms)
ms=re.sub(r'\s*BoxCard\("SESSION SAFETY",\(s\.sessionSafety\+"\\\\n"\+s\.supervisor\)\.trim\(\)\.ifBlank\{"UNAVAILABLE — session safety state not published\."\},true\)','',ms)
# Defensive removal if formatting changed in an earlier generator.
ms=ms.replace('BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)','')
ms=ms.replace('BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)','')
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • MATCHED MODULE SYNC')
m.write_text(ms)
print('R23_CC_SYNC=DJAEGER_CC_SYNC_V2')
print('R23_INTERNAL_PANELS=REMOVED_FROM_UI_ONLY')
print('R23_SYSFS_AUTHORITY=READ_ONLY_UNCHANGED')
