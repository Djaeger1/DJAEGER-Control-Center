#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12200',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r20"',bs,count=1); b.write_text(bs)
rs=r.read_text()
rs=rs.replace('val memoryStatus:String="",val envelope:String=""','val memoryStatus:String="",val authority:String="",val sessionSafety:String="",val supervisor:String="",val envelope:String=""',1)
rs=rs.replace("echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __ENV__;", "echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __AUTHORITY__; tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null\n        echo __SESSION_SAFETY__; cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null\n        echo __SUPERVISOR__; printf 'PID='; cat '$persistent/supervisor.pid' 2>/dev/null; printf '\\nHEARTBEAT='; cat '$persistent/supervisor.heartbeat' 2>/dev/null; printf '\\n'\n        echo __ENV__;",1)
rs=rs.replace('memoryStatus=section("MEMORY","ENV").trim(),envelope=section("ENV","HTTP").trim()', 'memoryStatus=section("MEMORY","AUTHORITY").trim(),authority=section("AUTHORITY","SESSION_SAFETY").trim(),sessionSafety=section("SESSION_SAFETY","SUPERVISOR").trim(),supervisor=section("SUPERVISOR","ENV").trim(),envelope=section("ENV","HTTP").trim()',1)
r.write_text(rs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r19 • THOUGHTS + MEMORY • FAST TELEMETRY','CONTROL CENTER • v0.12.1-r20 • UNIFIED RUNTIME CONTRACT',1)
# Keep legacy diagnostic code compile-safe but remove its misleading UI cards; replace exact card invocations.
patterns=[
 r'BoxCard\("DJAEGER AI ↔ KERNEL AUTHORITY SYNC",authorityStatus,true\)',
 r'BoxCard\("LIVE KERNEL CAPABILITY",kernelStatus,true\)',
 r'BoxCard\("SESSION RECOVERY",recoveryStatus,true\)',
 r'BoxCard\("SESSION SNAPSHOT LIFECYCLE",snapshotStatus,true\)',
 r'BoxCard\("MATURITY / REGRESSION AUDIT",auditStatus,true\)']
for p in patterns: ms=re.sub(p,'',ms)
# Insert the two useful runtime cards once near AI content.
needle='Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){'
pos=ms.find(needle,ms.find('@Composable fun AI'))
if pos>=0:
    end=pos+len(needle)
    cards='''\n        BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)\n        BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)'''
    ms=ms[:end]+cards+ms[end:]
# If source uses alternate formatting, at minimum eliminate the old titles from visible UI.
ms=ms.replace('"DJAEGER AI ↔ KERNEL AUTHORITY SYNC"','"KERNEL AUTHORITY LEGACY"').replace('"LIVE KERNEL CAPABILITY"','"KERNEL CAPABILITY LEGACY"').replace('"SESSION RECOVERY"','"SESSION RECOVERY LEGACY"').replace('"SESSION SNAPSHOT LIFECYCLE"','"SNAPSHOT LIFECYCLE LEGACY"').replace('"MATURITY / REGRESSION AUDIT"','"REGRESSION AUDIT LEGACY"')
m.write_text(ms)
print('R20_RUNTIME_CONTRACT=AUTHORITY+SESSION_SAFETY+SUPERVISOR')
