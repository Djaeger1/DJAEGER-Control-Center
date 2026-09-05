#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

# Material feature: expose two additional Cloudflare credential slots while
# preserving R32 runtime-truth mapping and all provider/authority semantics.
# Runtime selection is automatic; the UI slot buttons only choose which slot is edited.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12330',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r33"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
anchor='''    suspend fun deleteCloudflareCredentials():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloudflare-credentials-delete",5000); Pair(rc==0,out.trim())\n    }\n\n'''
assert anchor in rs, 'R33 cloudflare repository anchor missing'
extra='''    suspend fun cloudflareCredentialsVaultStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloudflare-credentials-vault-status",5000); Pair(rc==0,out.trim())\n    }\n    suspend fun saveCloudflareCredentialsSlot(slot:Int, accountId:String, apiToken:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(slot !in 1..3) return@withContext Pair(false,"CLOUDFLARE_SLOT_REJECTED=INVALID")\n        val a=accountId.trim(); val t=apiToken.trim()\n        if(a.isBlank() || t.isBlank()) return@withContext Pair(false,"CLOUDFLARE_CREDENTIALS_REJECTED=MISSING_FIELD")\n        val (rc,out)=suStdin("djaeger-ai cloudflare-credentials-slot-stdin $slot",a+"\\n"+t); Pair(rc==0,out.trim())\n    }\n    suspend fun removeCloudflareCredentialsSlot(slot:Int):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(slot !in 1..3) return@withContext Pair(false,"CLOUDFLARE_SLOT_REMOVE_REJECTED=INVALID")\n        val (rc,out)=su("djaeger-ai cloudflare-credentials-remove $slot",5000); Pair(rc==0,out.trim())\n    }\n\n'''
if 'suspend fun cloudflareCredentialsVaultStatus()' not in rs:
    rs=rs.replace(anchor,anchor+extra,1)
for x in ['cloudflare-credentials-vault-status','cloudflare-credentials-slot-stdin $slot','cloudflare-credentials-remove $slot']:
    assert x in rs, 'R33 repository bridge missing: '+x
assert 'selectCloudflareCredentialsSlot' not in rs
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r32 • RUNTIME TRUTH MAPPING','CONTROL CENTER • v0.12.1-r33 • CLOUDFLARE 3 AUTO SLOTS',1).replace('v0.12.1-r32','v0.12.1-r33')

state='''    var cloudflareAccountInput by remember{mutableStateOf("")}; var cloudflareTokenInput by remember{mutableStateOf("")}; var cloudflareStatus by remember{mutableStateOf("Checking Cloudflare credentials...")}'''
assert state in ms, 'R33 Cloudflare UI state anchor missing'
ms=ms.replace(state,state+'\n    var cloudflareSlot by remember{mutableStateOf(1)}',1)

old='''                val cf=repo.cloudflareCredentialsStatus();cloudflareStatus=cf.second.ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"}\n                val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}'''
new='''                val cf=repo.cloudflareCredentialsStatus();val cfv=repo.cloudflareCredentialsVaultStatus();cloudflareStatus=(cfv.second+"\\n"+cf.second).trim().ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"}\n                val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}'''
assert old in ms, 'R33 Cloudflare status refresh anchor missing'
ms=ms.replace(old,new,1)

old='''            "CLOUDFLARE_STATUS"->{val cf=repo.cloudflareCredentialsStatus();cloudflareStatus=cf.second.ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_SAVE"->{val cf=repo.saveCloudflareCredentials(cloudflareAccountInput,cloudflareTokenInput);cloudflareStatus=cf.second;if(cf.first){cloudflareAccountInput="";cloudflareTokenInput=""};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_DELETE"->{val cf=repo.deleteCloudflareCredentials();cloudflareStatus=cf.second;val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}'''
new='''            "CLOUDFLARE_STATUS"->{val cf=repo.cloudflareCredentialsStatus();val cfv=repo.cloudflareCredentialsVaultStatus();cloudflareStatus=(cfv.second+"\\n"+cf.second).trim().ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_SAVE"->{val cf=repo.saveCloudflareCredentialsSlot(cloudflareSlot,cloudflareAccountInput,cloudflareTokenInput);cloudflareStatus=cf.second;if(cf.first){cloudflareAccountInput="";cloudflareTokenInput=""};val cfv=repo.cloudflareCredentialsVaultStatus();cloudflareStatus=(cfv.second+"\\n"+cloudflareStatus).trim();val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_REMOVE"->{val cf=repo.removeCloudflareCredentialsSlot(cloudflareSlot);val cfv=repo.cloudflareCredentialsVaultStatus();cloudflareStatus=(cfv.second+"\\n"+cf.second).trim();val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}'''
assert old in ms, 'R33 Cloudflare operations anchor missing'
ms=ms.replace(old,new,1)

old='''        BoxCard("CLOUDFLARE CREDENTIAL STATUS",cloudflareStatus,true)\n        OutlinedTextField(value=cloudflareAccountInput,onValueChange={cloudflareAccountInput=it.take(64)},label={Text("Cloudflare Account ID")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        OutlinedTextField(value=cloudflareTokenInput,onValueChange={cloudflareTokenInput=it.take(512)},label={Text("Cloudflare API Token")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={bridgeOp="CLOUDFLARE_SAVE"},enabled=bridgeOp==null&&cloudflareAccountInput.isNotBlank()&&cloudflareTokenInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE / REPLACE")}\n            Button(onClick={bridgeOp="CLOUDFLARE_STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}\n            Button(onClick={bridgeOp="CLOUDFLARE_DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}\n        }'''
new='''        BoxCard("CLOUDFLARE CREDENTIAL SLOTS",cloudflareStatus,true)\n        Text("Edit slot: $cloudflareSlot • penggunaan otomatis: sticky healthy → failover 401/403/429",fontFamily=FontFamily.Monospace)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={cloudflareSlot=1},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SLOT 1")}\n            Button(onClick={cloudflareSlot=2},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SLOT 2")}\n            Button(onClick={cloudflareSlot=3},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SLOT 3")}\n        }\n        OutlinedTextField(value=cloudflareAccountInput,onValueChange={cloudflareAccountInput=it.take(64)},label={Text("Cloudflare Account ID • Slot $cloudflareSlot")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        OutlinedTextField(value=cloudflareTokenInput,onValueChange={cloudflareTokenInput=it.take(512)},label={Text("Cloudflare API Token • Slot $cloudflareSlot")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={bridgeOp="CLOUDFLARE_SAVE"},enabled=bridgeOp==null&&cloudflareAccountInput.isNotBlank()&&cloudflareTokenInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE SLOT")}\n            Button(onClick={bridgeOp="CLOUDFLARE_STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}\n            Button(onClick={bridgeOp="CLOUDFLARE_REMOVE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REMOVE SLOT")}\n        }'''
assert old in ms, 'R33 Cloudflare UI block anchor missing'
ms=ms.replace(old,new,1)

# Preservation gates: R31 dynamic narrative + R32 truth mapping remain untouched.
for x in [
    'val publishedThoughtText=thoughtField(s.thoughts,"TEXT").trim()',
    'cloudNarrativeFresh->"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"',
    'Decision source: ${x.source}',
    'Learning confidence: $lc',
    'BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)',
    'BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)',
]: assert x in ms, 'R33 preservation missing: '+x
for x in ['Text("SLOT 1")','Text("SLOT 2")','Text("SLOT 3")','CLOUDFLARE_REMOVE','saveCloudflareCredentialsSlot(cloudflareSlot','sticky healthy → failover 401/403/429']:
    assert x in ms, 'R33 slot UI missing: '+x
assert 'CLOUDFLARE_SELECT' not in ms
assert 'Text("USE SLOT")' not in ms
m.write_text(ms)

print('R33_CLOUDFLARE_SLOTS=3')
print('R33_SLOT_SELECTION=AUTO_STICKY_HEALTHY_FAILOVER')
print('R33_FAILOVER_SCOPE=401_403_429')
print('R33_SLOT_WRITE=STDIN_ONLY')
print('R33_LEGACY_SLOT1=PRESERVED_BY_BACKEND')
print('R33_R31_DYNAMIC_REASONING=PRESERVED')
print('R33_R32_RUNTIME_TRUTH=PRESERVED')
print('R33_PROVIDER_EQUALITY=UNCHANGED')
