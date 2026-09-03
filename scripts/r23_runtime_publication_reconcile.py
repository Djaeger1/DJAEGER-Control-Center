#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r87 canonical publications first, retain legacy fallbacks for older baselines.
rs=rs.replace("echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi", "echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai authority-sync status 2>/dev/null || tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi",1)
rs=rs.replace("echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; else cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; fi", "echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai session-recovery-status 2>/dev/null || true; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; else cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; fi",1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • R87 RUNTIME RECONCILE',1).replace('v0.12.1-r22','v0.12.1-r23')
# Runtime semantics: historical promoted plan is explicitly history, never current execution proof.
ms=ms.replace('STALE SNAPSHOT — NOT CURRENT RUNTIME','HISTORY SNAPSHOT — LAST PROMOTED, NOT CURRENT RUNTIME')
ms=ms.replace('Source: —','Source: HISTORY / LAST PROMOTED')
ms=ms.replace('APPLIED: UNAVAILABLE — requires fresh\nEXECUTION','APPLIED: IDLE — no fresh execution')
ms=ms.replace('READBACK VERIFIED: UNAVAILABLE — no\nverified readback evidence','READBACK VERIFIED: IDLE — no fresh execution/readback')
# If canonical state is temporarily absent, explain reconciliation rather than implying authority failure.
ms=ms.replace('UNAVAILABLE — authority state not published.','WAITING — canonical authority publication not available yet; live reconciliation will be attempted.')
ms=ms.replace('UNAVAILABLE — session safety state not published.','WAITING — canonical session safety publication not available yet; recovery reconciliation will be attempted.')
m.write_text(ms)
print('R23_CONTRACT=R87_CANONICAL_FIRST_WITH_LIVE_FALLBACK')
print('R23_HISTORY_SEMANTICS=NO_FALSE_RUNTIME_FAILURE')
print('R23_AUTHORITY=LOCAL_EXECUTOR_UNCHANGED')
