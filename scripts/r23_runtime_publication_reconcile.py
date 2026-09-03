#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# R87 canonical publications first. Inject live fallback without depending on an exact legacy line shape.
old=rs
rs=re.sub(r"echo __AUTHORITY__;\s*if \[ -s '\$persistent/authority_state\.env' \]; then cat '\$persistent/authority_state\.env';\s*else\s*tail -n 12 '\$persistent/authority_sync_boot\.log' 2>/dev/null;\s*fi", "echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai authority-sync status 2>/dev/null || tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi", rs, count=1)
# If R21/R22 already changed formatting, append explicit live reconciliation to the authority section.
if 'djaeger-ai authority-sync status' not in rs:
    rs=rs.replace("echo __AUTHORITY__;", "echo __AUTHORITY__; if [ ! -s '$persistent/authority_state.env' ] && command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai authority-sync status 2>/dev/null || true; fi;",1)
rs=re.sub(r"echo __SESSION_SAFETY__;\s*if \[ -s '\$persistent/session_safety\.env' \]; then cat '\$persistent/session_safety\.env';\s*else\s*cat '\$persistent/session_recovery_state' 2>/dev/null;\s*printf 'SNAPSHOT_LAST=';\s*tail -n 1 '\$persistent/snapshot_lifecycle\.log' 2>/dev/null;\s*fi", "echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; elif command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai session-recovery-status 2>/dev/null || true; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; else cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; fi", rs, count=1)
if 'djaeger-ai session-recovery-status' not in rs:
    rs=rs.replace("echo __SESSION_SAFETY__;", "echo __SESSION_SAFETY__; if [ ! -s '$persistent/session_safety.env' ] && command -v djaeger-ai >/dev/null 2>&1; then djaeger-ai session-recovery-status 2>/dev/null || true; fi;",1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • R87 RUNTIME RECONCILE',1).replace('v0.12.1-r22','v0.12.1-r23')
ms=ms.replace('STALE SNAPSHOT — NOT CURRENT RUNTIME','HISTORY SNAPSHOT — LAST PROMOTED, NOT CURRENT RUNTIME')
ms=ms.replace('Source: —','Source: HISTORY / LAST PROMOTED')
# Preserve truthful idle semantics even when source formatting changed between R15-R22.
ms=re.sub(r'APPLIED: UNAVAILABLE[^"\n]*', 'APPLIED: IDLE — no fresh execution', ms)
ms=re.sub(r'READBACK VERIFIED: UNAVAILABLE[^"\n]*', 'READBACK VERIFIED: IDLE — no fresh execution/readback', ms)
ms=ms.replace('UNAVAILABLE — authority state not published.','WAITING — canonical authority publication not available yet; live reconciliation will be attempted.')
ms=ms.replace('UNAVAILABLE — session safety state not published.','WAITING — canonical session safety publication not available yet; recovery reconciliation will be attempted.')
m.write_text(ms)
assert 'djaeger-ai authority-sync status' in rs
assert 'djaeger-ai session-recovery-status' in rs
print('R23_CONTRACT=R87_CANONICAL_FIRST_WITH_LIVE_FALLBACK')
print('R23_HISTORY_SEMANTICS=NO_FALSE_RUNTIME_FAILURE')
print('R23_AUTHORITY=LOCAL_EXECUTOR_UNCHANGED')
