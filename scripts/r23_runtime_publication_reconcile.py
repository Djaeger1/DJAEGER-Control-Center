#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
auth="echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai authority-sync status 2>/dev/null || tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi"
sess="echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai session-recovery-status 2>/dev/null || cat '$persistent/session_recovery_state' 2>/dev/null; else cat '$persistent/session_recovery_state' 2>/dev/null; fi; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null"
sup="echo __SUPERVISOR__; printf 'PID='; cat '$persistent/supervisor.pid' 2>/dev/null; printf '\\nHEARTBEAT='; cat '$persistent/supervisor.heartbeat' 2>/dev/null; printf '\\n'"
if '__AUTHORITY__' in rs:
    rs=re.sub(r"echo __AUTHORITY__;.*?(?=\s*echo __SESSION_SAFETY__;)",auth+'\n        ',rs,count=1,flags=re.S)
    rs=re.sub(r"echo __SESSION_SAFETY__;.*?(?=\s*echo __SUPERVISOR__;)",sess+'\n        ',rs,count=1,flags=re.S)
else:
    # R20/R21 transforms can be no-ops when the generated snapshot formatting differs.
    # Inject all R87 sections directly before the stable ENV section.
    anchor='echo __ENV__;'
    if anchor not in rs: raise SystemExit('R23 snapshot ENV anchor missing')
    rs=rs.replace(anchor,auth+'\n        '+sess+'\n        '+sup+'\n        '+anchor,1)
# Ensure Snapshot data model/parser has the R20 fields even if R20 formatting transform missed.
if 'val authority:String' not in rs:
    rs=rs.replace('val memoryStatus:String="",val envelope:String=""','val memoryStatus:String="",val authority:String="",val sessionSafety:String="",val supervisor:String="",val envelope:String=""',1)
if 'authority=section("AUTHORITY"' not in rs:
    rs=rs.replace('memoryStatus=section("MEMORY","ENV").trim(),envelope=section("ENV","HTTP").trim()','memoryStatus=section("MEMORY","AUTHORITY").trim(),authority=section("AUTHORITY","SESSION_SAFETY").trim(),sessionSafety=section("SESSION_SAFETY","SUPERVISOR").trim(),supervisor=section("SUPERVISOR","ENV").trim(),envelope=section("ENV","HTTP").trim()',1)
r.write_text(rs)
ms=m.read_text(); ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • R87 RUNTIME RECONCILE',1).replace('v0.12.1-r22','v0.12.1-r23'); ms=ms.replace('STALE SNAPSHOT — NOT CURRENT RUNTIME','HISTORY SNAPSHOT — LAST PROMOTED, NOT CURRENT RUNTIME'); ms=ms.replace('Source: —','Source: HISTORY / LAST PROMOTED'); ms=ms.replace('UNAVAILABLE — authority state not published.','WAITING — canonical authority publication not available yet; live reconciliation will be attempted.'); ms=ms.replace('UNAVAILABLE — session safety state not published.','WAITING — canonical session safety publication not available yet; recovery reconciliation will be attempted.'); m.write_text(ms)
for x in ['authority_state.env','session_safety.env','djaeger-ai authority-sync status','djaeger-ai session-recovery-status','__AUTHORITY__','__SESSION_SAFETY__','__SUPERVISOR__']:
    assert x in rs,x
print('R23_CONTRACT=R87_CANONICAL_FIRST_WITH_LIVE_FALLBACK'); print('R23_HISTORY_SEMANTICS=NO_FALSE_RUNTIME_FAILURE'); print('R23_AUTHORITY=LOCAL_EXECUTOR_UNCHANGED')
