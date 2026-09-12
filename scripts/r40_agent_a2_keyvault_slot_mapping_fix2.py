#!/usr/bin/env python3
from pathlib import Path

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()

# Use a lifecycle-aware Compose scope for explicit key-pool sync instead of an ad-hoc Main CoroutineScope.
ai_start=s.index('@Composable fun AI(s:RuntimeState)')
ai_end=s.index('private fun aiSummary',ai_start)
ai=s[ai_start:ai_end]
if 'val uiScope=rememberCoroutineScope()' not in ai:
    ai=ai.replace('val repo=remember{DjaegerRepository()};','val repo=remember{DjaegerRepository()};val uiScope=rememberCoroutineScope();',1)

old_sync='''Button(onClick={ val keys=vault4.configuredKeys(); kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main).launch { repo.syncGeminiKeyPool(keys,vault4.active()); vaultEpoch++ } }, enabled=vault4.configuredKeys().isNotEmpty()){ Text("SYNC 4-KEY POOL") }'''
new_sync='''Button(onClick={ val entries=(1..4).mapNotNull{slot->vault4.get(slot)?.let{k->slot to k}}; val keys=entries.map{it.second}; val preferred=(entries.indexOfFirst{it.first==vault4.active()}+1).let{if(it>0)it else 1}; uiScope.launch { repo.syncGeminiKeyPool(keys,preferred); vaultEpoch++ } }, enabled=vault4.configuredKeys().isNotEmpty()){ Text("SYNC 4-KEY POOL") }'''
assert old_sync in ai,'R40_FAIL=pool-sync-anchor'
ai=ai.replace(old_sync,new_sync,1)

old_select='''Button(onClick={ val k=vault4.get(vaultSlot); if(k!=null){ keyInput=k; bridgeOp="SAVE" } },modifier=Modifier.weight(1f)){Text("SELECT")}'''
new_select='''Button(onClick={ val k=vault4.get(vaultSlot); if(k!=null){ vault4.setActive(vaultSlot); keyInput=k; bridgeOp="SAVE"; vaultEpoch++ } },modifier=Modifier.weight(1f)){Text("SELECT")}'''
assert old_select in ai,'R40_FAIL=select-anchor'
ai=ai.replace(old_select,new_select,1)

s=s[:ai_start]+ai+s[ai_end:]
p.write_text(s)
S=p.read_text()
assert 'val uiScope=rememberCoroutineScope()' in S
assert 'vault4.setActive(vaultSlot)' in S
assert 'entries.indexOfFirst{it.first==vault4.active()}' in S
assert 'CoroutineScope(kotlinx.coroutines.Dispatchers.Main)' not in S
print('R40_KEYVAULT_ACTIVE_SLOT=PASS')
print('R40_KEYVAULT_COMPRESSED_INDEX_MAPPING=PASS')
print('R40_LIFECYCLE_SCOPE=PASS')
