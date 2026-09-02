#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12210',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r21"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r86 publishes first-class files; prefer them and retain r20 legacy fallback data.
rs=rs.replace("echo __AUTHORITY__; tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null", "echo __AUTHORITY__; if [ -s '$persistent/authority_state.env' ]; then cat '$persistent/authority_state.env'; else tail -n 12 '$persistent/authority_sync_boot.log' 2>/dev/null; fi",1)
rs=rs.replace("echo __SESSION_SAFETY__; cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null", "echo __SESSION_SAFETY__; if [ -s '$persistent/session_safety.env' ]; then cat '$persistent/session_safety.env'; else cat '$persistent/session_recovery_state' 2>/dev/null; printf 'SNAPSHOT_LAST='; tail -n 1 '$persistent/snapshot_lifecycle.log' 2>/dev/null; fi",1)
r.write_text(rs)
ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r20 • UNIFIED RUNTIME CONTRACT','CONTROL CENTER • v0.12.1-r21 • RUNTIME BUGFIX',1)
# Local Android vault is an editor/staging vault. Runtime truth must come from module masked vault status.
old='val vaultStatus4=remember(vaultEpoch){vault4.status()+"\\n"+vault4.rotationStatus()}'
new='''var moduleVaultStatus by remember { mutableStateOf("") }
        LaunchedEffect(vaultEpoch) { moduleVaultStatus = repo.geminiKeyVaultStatus() }
        val vaultStatus4 = moduleVaultStatus.ifBlank { vault4.status()+"\\nLOCAL STAGING ONLY • runtime vault status unavailable" }'''
assert old in ms; ms=ms.replace(old,new,1)
# Refresh module vault truth after explicit sync/select/delete UI activity instead of presenting stale local EMPTY state.
ms=ms.replace('repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++','repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++',1)
# Copy label must remain single line on narrow/freeform windows.
ms=ms.replace('Text("COPY")','Text("COPY",maxLines=1)',20)
# Never render a missing numeric thermal sample as a real 0 C measurement.
for fld in ['cpu','gpu','skin','battery','cpuTemp','gpuTemp','skinTemp','batteryTemp']:
    ms=ms.replace('${s.'+fld+'}°C','${if(s.'+fld+'.toString()=="0"||s.'+fld+'.toString()=="0.0") "—" else s.'+fld+'.toString()+"°C"}')
m.write_text(ms)
print('R21_VAULT_TRUTH=MODULE_MASKED_STATUS')
print('R21_CONTRACT=R86_FIRST_CLASS_WITH_LEGACY_FALLBACK')
print('R21_COPY=NARROW_LAYOUT_SAFE')
print('R21_MISSING_THERMAL=UNAVAILABLE_NOT_ZERO')
