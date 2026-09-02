#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12200',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r20"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r19 generator is applied by workflow before this patch; add authority/session safety fields to its RuntimeState.
rs=rs.replace('val memoryStatus:String="",val envelope:String=""','val memoryStatus:String="",val authority:String="",val sessionSafety:String="",val supervisor:String="",val envelope:String=""',1)
rs=rs.replace("echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __ENV__;", "echo __MEMORY__; cat '$persistent/local_memory_status.env' 2>/dev/null\n        echo __AUTHORITY__; tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null\n        echo __SESSION_SAFETY__; cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null\n        echo __SUPERVISOR__; printf 'PID='; cat '$persistent/supervisor.pid' 2>/dev/null; printf '\\nHEARTBEAT='; cat '$persistent/supervisor.heartbeat' 2>/dev/null; printf '\\n'\n        echo __ENV__;",1)
rs=rs.replace('memoryStatus=section("MEMORY","ENV").trim(),envelope=section("ENV","HTTP").trim()', 'memoryStatus=section("MEMORY","AUTHORITY").trim(),authority=section("AUTHORITY","SESSION_SAFETY").trim(),sessionSafety=section("SESSION_SAFETY","SUPERVISOR").trim(),supervisor=section("SUPERVISOR","ENV").trim(),envelope=section("ENV","HTTP").trim()',1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r19 • THOUGHTS + MEMORY • FAST TELEMETRY','CONTROL CENTER • v0.12.1-r20 • UNIFIED RUNTIME CONTRACT',1)
# Remove manual developer-only diagnostic state and operations from AI page.
for line in [
'    var authorityStatus by remember{mutableStateOf("Authority sync not loaded yet.")}\n',
'    var kernelStatus by remember{mutableStateOf("Kernel capability not loaded yet.")}\n',
'    var auditStatus by remember{mutableStateOf("Maturity audit not run yet.")}\n',
'    var recoveryStatus by remember{mutableStateOf("Recovery state not loaded yet.")}\n',
'    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}\n']:
    ms=ms.replace(line,'')
for op in ['            "AUTHORITY"->{val r=repo.authoritySyncStatus();authorityStatus=r.second.ifBlank{"AUTHORITY_SYNC=EMPTY"}}\n','            "KERNEL"->{val r=repo.kernelCapabilitySummary();kernelStatus=r.second.ifBlank{"KERNEL_CAPABILITY=EMPTY"}}\n','            "AUDIT"->{val r=repo.maturityAudit();auditStatus=r.second.ifBlank{"MATURITY_AUDIT=EMPTY"}}\n','            "RECOVERY"->{val r=repo.recoveryStatus();recoveryStatus=r.second.ifBlank{"RECOVERY_STATUS=EMPTY"}}\n','            "SNAPSHOT"->{val r=repo.snapshotLifecycleStatus();snapshotStatus=r.second.ifBlank{"SNAPSHOT_STATUS=EMPTY"}}\n']:
    ms=ms.replace(op,'')
# Replace five legacy cards with two live contract cards. Regex intentionally spans only these known BoxCards.
pat=re.compile(r'\s*BoxCard\("DJAEGER AI ↔ KERNEL AUTHORITY SYNC".*?BoxCard\("MATURITY / REGRESSION AUDIT".*?\)\s*',re.S)
replacement='''\n        val auth=s.authority.ifBlank{"UNAVAILABLE — module has not published authority state."}\n        val safety=s.sessionSafety.ifBlank{"UNAVAILABLE — module has not published session safety state."}\n        val sup=s.supervisor.ifBlank{"UNAVAILABLE — supervisor heartbeat not published."}\n        BoxCard("KERNEL AUTHORITY",auth,true)\n        BoxCard("SESSION SAFETY",safety+"\\n"+sup,true)\n'''
ms,n=pat.subn(replacement,ms,count=1)
if n!=1:
    # Fallback: insert useful cards even if legacy source formatting changed; hide misleading placeholder text.
    ms=ms.replace('Text("DJAEGER AI / GEMINI",color=Green,fontWeight=FontWeight.Bold)', 'Text("DJAEGER AI / GEMINI",color=Green,fontWeight=FontWeight.Bold); BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true); BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).ifBlank{"UNAVAILABLE — session safety state not published."},true)',1)
    for txt in ['Authority sync not loaded yet.','Kernel capability not loaded yet.','Recovery state not loaded yet.','Snapshot lifecycle not loaded yet.','Maturity audit not run yet.']:
        ms=ms.replace(txt,'UNAVAILABLE')
m.write_text(ms)
print('R20_RUNTIME_CONTRACT=AUTHORITY+SESSION_SAFETY+SUPERVISOR')
print('R20_LEGACY_PLACEHOLDERS=REMOVED_OR_FAILSOFT')
print('R20_MATURITY_AUDIT_UI=REMOVED')
