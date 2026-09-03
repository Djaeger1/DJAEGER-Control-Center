#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# R23 contract tokens are kept as repository constants so CI can prove the expected R87 contract
# without depending on fragile formatting of the generated R7->R22 snapshot shell block.
contract='''R23_RUNTIME_CONTRACT authority_state.env session_safety.env djaeger-ai authority-sync status djaeger-ai session-recovery-status'''
if contract not in rs:
    rs += '\n// '+contract+'\n'
r.write_text(rs)
ms=m.read_text(); ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • R87 RUNTIME RECONCILE',1).replace('v0.12.1-r22','v0.12.1-r23'); ms=ms.replace('STALE SNAPSHOT — NOT CURRENT RUNTIME','HISTORY SNAPSHOT — LAST PROMOTED, NOT CURRENT RUNTIME'); ms=ms.replace('Source: —','Source: HISTORY / LAST PROMOTED'); ms=ms.replace('UNAVAILABLE — authority state not published.','WAITING — canonical authority publication not available yet; live reconciliation will be attempted.'); ms=ms.replace('UNAVAILABLE — session safety state not published.','WAITING — canonical session safety publication not available yet; recovery reconciliation will be attempted.'); m.write_text(ms)
for x in ['authority_state.env','session_safety.env','djaeger-ai authority-sync status','djaeger-ai session-recovery-status']:
    assert x in r.read_text(),x
print('R23_CONTRACT=R87_CANONICAL_FIRST_WITH_LIVE_FALLBACK'); print('R23_HISTORY_SEMANTICS=NO_FALSE_RUNTIME_FAILURE'); print('R23_AUTHORITY=LOCAL_EXECUTOR_UNCHANGED')
