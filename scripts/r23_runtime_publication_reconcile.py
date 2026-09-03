#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Make the R87 canonical publication files explicit in the generated snapshot command.
# R87 guardian owns these files; Control Center remains read-only and falls back to djaeger-ai status.
auth="echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai authority-sync status 2>/dev/null || tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi;"
sess="echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai session-recovery-status 2>/dev/null || cat '$persistent/session_recovery_state' 2>/dev/null; else cat '$persistent/session_recovery_state' 2>/dev/null; fi; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null;"
# Replace the complete generated authority/session shell fragments by marker boundaries.
rs,n1=re.subn(r"echo __AUTHORITY__;.*?(?=echo __SESSION_SAFETY__;)",auth+' ',rs,count=1,flags=re.S)
rs,n2=re.subn(r"echo __SESSION_SAFETY__;.*?(?=echo __SUPERVISOR__;)",sess+' ',rs,count=1,flags=re.S)
if n1 != 1 or n2 != 1:
    raise SystemExit(f'R23 snapshot marker reconciliation failed authority={n1} session={n2}')
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • R87 RUNTIME RECONCILE',1).replace('v0.12.1-r22','v0.12.1-r23')
ms=ms.replace('STALE SNAPSHOT — NOT CURRENT RUNTIME','HISTORY SNAPSHOT — LAST PROMOTED, NOT CURRENT RUNTIME')
ms=ms.replace('Source: —','Source: HISTORY / LAST PROMOTED')
ms=re.sub(r'APPLIED: UNAVAILABLE[^"\n]*','APPLIED: IDLE — no fresh execution',ms)
ms=re.sub(r'READBACK VERIFIED: UNAVAILABLE[^"\n]*','READBACK VERIFIED: IDLE — no fresh execution/readback',ms)
ms=ms.replace('UNAVAILABLE — authority state not published.','WAITING — canonical authority publication not available yet; live reconciliation will be attempted.')
ms=ms.replace('UNAVAILABLE — session safety state not published.','WAITING — canonical session safety publication not available yet; recovery reconciliation will be attempted.')
m.write_text(ms)
assert 'authority_state.env' in rs and 'session_safety.env' in rs
assert 'djaeger-ai authority-sync status' in rs and 'djaeger-ai session-recovery-status' in rs
print('R23_CONTRACT=R87_CANONICAL_FIRST_WITH_LIVE_FALLBACK')
print('R23_HISTORY_SEMANTICS=NO_FALSE_RUNTIME_FAILURE')
print('R23_AUTHORITY=LOCAL_EXECUTOR_UNCHANGED')
