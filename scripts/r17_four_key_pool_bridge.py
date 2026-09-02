#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'; kv=root/'app/src/main/java/com/djaeger/controlcenter/KeyVault4.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12170',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r17"',bs,count=1); b.write_text(bs)
rs=r.read_text()
anchor='    suspend fun geminiKeyVaultStatus()'; assert anchor in rs
bridge='''    suspend fun syncGeminiKeyPool(keys: List<String>, preferredSlot: Int): String = withContext(Dispatchers.IO) {\n        val clean = keys.map { it.trim() }.filter { it.isNotEmpty() }.take(4)\n        if (clean.isEmpty()) return@withContext "NO_KEYS"\n        val (clearRc, _) = su("djaeger-ai gemini-key-delete", 5000)\n        if (clearRc != 0) return@withContext "CLEAR_FAILED"\n        for (key in clean) {\n            val (addRc, _) = suStdin("djaeger-ai gemini-key-add-stdin", key)\n            if (addRc != 0) return@withContext "SYNC_FAILED"\n        }\n        val selected = preferredSlot.coerceIn(1, clean.size)\n        val (selectRc, _) = su("djaeger-ai gemini-key-select $selected", 5000)\n        if (selectRc != 0) "SELECT_FAILED" else "SYNCED ${clean.size}/4 • ACTIVE $selected"\n    }\n\n'''
rs=rs.replace(anchor,bridge+anchor,1); r.write_text(rs)
ks=kv.read_text()
if 'fun configuredKeys' not in ks: ks=ks.replace('fun rotationStatus():String=', 'fun configuredKeys(): List<String> = (1..4).mapNotNull { get(it) }\nfun rotationStatus():String=',1)
kv.write_text(ks)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r16 • SESSION/FRAME CONTRACT • REALTIME 1s','CONTROL CENTER • v0.12.1-r17 • 4-KEY POOL • REALTIME 1s')
if 'import kotlinx.coroutines.launch' not in ms:
    pkg_end=ms.find('\n',ms.find('package ')); ms=ms[:pkg_end+1]+'import kotlinx.coroutines.launch\n'+ms[pkg_end+1:]
needle='Text(vaultStatus4'; pos=ms.find(needle)
button='                Button(onClick={ val keys=vault4.configuredKeys(); kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main).launch { repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++ } }, enabled=vault4.configuredKeys().isNotEmpty()){ Text("SYNC 4-KEY POOL") }\n'
if pos>=0:
    line_end=ms.find('\n',pos); ms=ms[:line_end+1]+button+ms[line_end+1:]
else:
    marker='GEMINI KEY VAULT • 4 MANUAL SLOTS'; p=ms.find(marker); assert p>=0; q=ms.find('\n',p); ms=ms[:q+1]+button+ms[q+1:]
m.write_text(ms)
print('R17_VAULT=4_ENCRYPTED_LOCAL_SLOTS');print('R17_BRIDGE=STDIN_ONLY_NO_SECRET_ARGS');print('R17_POOL_SYNC=EXPLICIT_NOT_REALTIME_REFRESH');print('R17_TRANSPORT_ROTATION=MODULE_OWNED')
