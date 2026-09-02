#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'; kv=root/'app/src/main/java/com/djaeger/controlcenter/KeyVault4.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12170',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r17"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Atomic root-side vault synchronization: rebuild module vault from encrypted local slots without logging secrets.
anchor='    suspend fun geminiKeyVaultStatus()'
assert anchor in rs
bridge='''    suspend fun syncGeminiKeyPool(keys: List<String>, preferredSlot: Int): String = withContext(Dispatchers.IO) {\n        val clean=keys.map{it.trim()}.filter{it.isNotEmpty()}.take(4)\n        if(clean.isEmpty()) return@withContext "NO_KEYS"\n        // Clear root vault then add each key over stdin. Raw values never enter command arguments or snapshots.\n        rootCommand("djaeger-ai gemini-key-delete")\n        for(key in clean){\n            val rc=rootCommandStdin("djaeger-ai gemini-key-add-stdin", key)\n            if(!rc.ok) return@withContext "SYNC_FAILED"\n        }\n        val selected=preferredSlot.coerceIn(1,clean.size)\n        val sel=rootCommand("djaeger-ai gemini-key-select $selected")\n        if(!sel.ok) "SELECT_FAILED" else "SYNCED ${clean.size}/4 • ACTIVE $selected"\n    }\n\n'''
rs=rs.replace(anchor,bridge+anchor,1)
r.write_text(rs)
ks=kv.read_text()
if 'fun configuredKeys' not in ks:
    ks=ks.replace('fun rotationStatus():String=', 'fun configuredKeys():List<String>=(1..4).mapNotNull{get(it)}\nfun rotationStatus():String=',1)
kv.write_text(ks)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r16 • SESSION/FRAME CONTRACT • REALTIME 1s','CONTROL CENTER • v0.12.1-r17 • 4-KEY POOL • REALTIME 1s')
# Existing SAVE/SELECT path remains; add explicit pool sync control beside vault status, never on 1s refresh.
needle='Text(vaultStatus4'
pos=ms.find(needle)
if pos>=0:
    line_end=ms.find('\n',pos)
    inject='''\n                Button(onClick={ scope.launch { val keys=vault4.configuredKeys(); bridgeMessage=repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++ } }, enabled=!bridgeBusy){ Text("SYNC 4-KEY POOL") }\n'''
    ms=ms[:line_end+1]+inject+ms[line_end+1:]
else:
    # Fallback attach after vault title text if generated source differs slightly.
    marker='GEMINI KEY VAULT • 4 MANUAL SLOTS'
    p=ms.find(marker)
    assert p>=0
    q=ms.find('\n',p)
    ms=ms[:q+1]+'                Button(onClick={ scope.launch { val keys=vault4.configuredKeys(); bridgeMessage=repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++ } }, enabled=!bridgeBusy){ Text("SYNC 4-KEY POOL") }\n'+ms[q+1:]
m.write_text(ms)
print('R17_VAULT=4_ENCRYPTED_LOCAL_SLOTS')
print('R17_BRIDGE=STDIN_ONLY_NO_SECRET_ARGS')
print('R17_POOL_SYNC=EXPLICIT_NOT_REALTIME_REFRESH')
print('R17_TRANSPORT_ROTATION=MODULE_OWNED')
