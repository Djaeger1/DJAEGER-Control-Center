#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12250',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r25"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('v0.12.1-r24','v0.12.1-r25').replace('CANONICAL RUNTIME READER','LIVE GEMINI + VAULT TRUTH')

# Hoist backend-vault UI state before bridge effects so status can be refreshed
# transactionally after CHAT/STATUS/VAULT operations.
state_anchor='    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}\n'
assert state_anchor in ms,'AI state anchor missing'
state_add='''    var vaultSlot by remember{mutableStateOf(1)}\n    var vaultEpoch by remember{mutableStateOf(0)}\n    var moduleVaultStatus by remember{mutableStateOf("")}\n'''
if 'var moduleVaultStatus by remember' not in ms[:ms.find('LaunchedEffect(request)')]:
    ms=ms.replace(state_anchor,state_anchor+state_add,1)

# Keep a stable copy of the operation. After a Gemini chat, immediately refresh
# key/transport status so an old 429 cannot remain visible as if it were current.
le='    LaunchedEffect(bridgeOp){\n'
assert le in ms,'bridge LaunchedEffect missing'
if 'val currentOp=bridgeOp' not in ms:
    ms=ms.replace(le,le+'        val currentOp=bridgeOp\n',1)

# Refresh status/vault after the command completes; this is event-driven only,
# never part of the 1-second recurring snapshot poll.
end_anchor='''        bridgeOp=null\n    }\n    val supported='''
assert end_anchor in ms,'bridge completion anchor missing'
refresh='''        if(currentOp=="CHAT") {\n            val (_,freshKeyStatus)=repo.geminiKeyStatus()\n            bridgeStatus=freshKeyStatus.ifBlank{"KEY_STATUS_UNAVAILABLE"}\n        }\n        if(currentOp in listOf("STATUS","SAVE","SAVE_KEY","DELETE","VAULT_STATUS","VAULT_ADD","VAULT_SELECT","VAULT_REMOVE","CHAT")) {\n            val (_,freshVault)=repo.geminiKeyVaultStatus()\n            moduleVaultStatus=freshVault.ifBlank{"VAULT_STATUS_UNAVAILABLE"}\n            vaultEpoch++\n        }\n        bridgeOp=null\n    }\n    val supported='''
ms=ms.replace(end_anchor,refresh,1)

# Remove the contradictory local AES-vault UI. R25 exposes one source of truth:
# the root-owned module vault. Slot buttons now select a backend slot, and the
# active key is whichever module line is marked ACTIVE=YES.
start=ms.find('val vaultContext=androidx.compose.ui.platform.LocalContext.current')
fast=ms.find('var fastTelemetryState by remember',start)
assert start>=0 and fast>start,'local vault block boundary missing'
backend_ui='''var moduleVaultStatusView = moduleVaultStatus.ifBlank { "VAULT_STATUS_UNAVAILABLE — tap REFRESH" }\n        BoxCard("GEMINI KEY VAULT • MODULE TRUTH",moduleVaultStatusView+"\\nSelected slot: KEY $vaultSlot\\nRuntime active key is the slot marked ACTIVE=YES above. Selection alone does not activate it.",true)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){(1..4).forEach{n->OutlinedButton(onClick={vaultSlot=n},modifier=Modifier.weight(1f)){Text("KEY $n")}}}\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={vaultIndex=vaultSlot.toString();bridgeOp="VAULT_SELECT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("ACTIVATE")}\n            Button(onClick={vaultIndex=vaultSlot.toString();bridgeOp="VAULT_REMOVE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REMOVE")}\n            Button(onClick={bridgeOp="VAULT_STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH VAULT")}\n        }\n        '''
ms=ms[:start]+backend_ui+ms[fast:]

# Make transport-status freshness explicit. It remains on-demand to preserve the
# single recurring cc_snapshot architecture.
ms=ms.replace('GEMINI KEY STATUS • CACHED LOCAL RECORD','GEMINI KEY STATUS • LAST OBSERVED — REFRESH / CHAT UPDATES')
ms=ms.replace('BoxCard("GEMINI KEY STATUS",bridgeStatus,true)','BoxCard("GEMINI KEY STATUS • LAST OBSERVED — REFRESH / CHAT UPDATES",bridgeStatus,true)')

m.write_text(ms)

M=m.read_text()
checks={
 'R25_VERSION':'v0.12.1-r25' in M,
 'SINGLE_VAULT_UI':'GEMINI KEY VAULT • MODULE TRUTH' in M and 'val vaultContext=androidx.compose.ui.platform.LocalContext.current' not in M,
 'ACTIVE_TRUTH':'Runtime active key is the slot marked ACTIVE=YES above' in M,
 'CHAT_REFRESH':'currentOp=="CHAT"' in M and 'repo.geminiKeyStatus()' in M,
 'VAULT_REFRESH':'repo.geminiKeyVaultStatus()' in M and 'VAULT_SELECT' in M and 'VAULT_REMOVE' in M,
 'NO_RECURRING_GEMINI_STATUS':'LaunchedEffect(s.updated)' not in M,
}
for k,v in checks.items(): print(f'{k}={"PASS" if v else "FAIL"}')
bad=[k for k,v in checks.items() if not v]
assert not bad,','.join(bad)
