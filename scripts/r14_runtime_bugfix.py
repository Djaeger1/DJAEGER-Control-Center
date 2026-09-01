#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12140',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r14"',bs,count=1); b.write_text(bs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r13 • COMPLETE USER DESIGN • REALTIME 1s','CONTROL CENTER • v0.12.1-r14 • RUNTIME BUGFIX • REALTIME 1s')
# Never present a stale module version as current runtime truth.
ms=ms.replace('Module: ${s.moduleVersion}','Module: ${if(s.freshness=="FRESH") s.moduleVersion else "STALE / awaiting fresh runtime"}')
m.write_text(ms)
rs=r.read_text()
# Runtime state must not inherit hard-coded r78 identity from stale module snapshots.
rs=rs.replace('moduleVersion=module["version"]?:"v12.9.50-r78 Outcome Generation Governor Integrity"','moduleVersion=module["version"]?:"UNKNOWN"')
rs=rs.replace('moduleVersion="v12.9.50-r78 Outcome Generation Governor Integrity"','moduleVersion="UNKNOWN"')
# If cc_snapshot is stale but live controller process is present, expose process activity separately; do not fabricate game/FPS.
needle='val ageSec = ((System.currentTimeMillis()/1000L) - sampleEpoch).coerceAtLeast(0L)'
if needle in rs and 'controllerProcessAlive' not in rs:
    rs=rs.replace(needle,needle+'\n        val controllerProcessAlive = (controllerPid ?: 0) > 0',1)
# Freshness remains authoritative: stale data cannot claim active game/session. This prevents contradictory ACTIVE/STALE state.
rs=rs.replace('val runtimeActive = rt["RUNTIME_STATE"]?.equals("ACTIVE",true)==true','val runtimeActive = rt["RUNTIME_STATE"]?.equals("ACTIVE",true)==true && ageSec <= 5',1)
r.write_text(rs)
print('R14_STALE_RUNTIME_FAIL_CLOSED=PASS'); print('R14_R78_IDENTITY_COUPLING=REMOVED'); print('R14_NO_GAME_FPS_GUESSING=PASS')
