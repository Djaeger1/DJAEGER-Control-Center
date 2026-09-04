#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12280',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r28"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
anchor='''    suspend fun cloudProviderStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloud-provider-status",5000); Pair(rc==0,out.trim())\n    }\n\n'''
assert anchor in rs, 'R28 repository cloud status anchor missing'
bridge='''    suspend fun cloudflareCredentialsStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloudflare-credentials-status",5000); Pair(rc==0,out.trim())\n    }\n    suspend fun saveCloudflareCredentials(accountId:String, apiToken:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val a=accountId.trim(); val t=apiToken.trim()\n        if(a.isBlank() || t.isBlank()) return@withContext Pair(false,"CLOUDFLARE_CREDENTIALS_REJECTED=MISSING_FIELD")\n        val (rc,out)=suStdin("djaeger-ai cloudflare-credentials-stdin",a+"\\n"+t); Pair(rc==0,out.trim())\n    }\n    suspend fun deleteCloudflareCredentials():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloudflare-credentials-delete",5000); Pair(rc==0,out.trim())\n    }\n\n'''
assert 'suspend fun cloudflareCredentialsStatus()' not in rs
rs=rs.replace(anchor,anchor+bridge,1)
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r27 • EQUAL CLOUD PEERS','CONTROL CENTER • v0.12.1-r28 • THREE EQUAL CLOUD PEERS',1).replace('v0.12.1-r27','v0.12.1-r28')
ms=ms.replace('Ask DJAEGER naturally. Gemini and Groq are equal cloud peers; one peer is active at a time, and Local AI is the final fallback.','Ask DJAEGER naturally. Gemini, Groq, and Cloudflare are equal cloud peers; exactly one peer is active at a time, and Local AI is the final fallback.')

anchor_badge='''        "GROQ"->"◇ GROQ • $status"'''
assert anchor_badge in ms, 'R28 source badge anchor missing'
ms=ms.replace(anchor_badge,anchor_badge+'\n        "CLOUDFLARE"->"◇ CLOUDFLARE • $status"',1)

old='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")\n    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")\n    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")\n    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}\n    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}\n    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState"'''
new='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")\n    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")\n    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")\n    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}\n    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}\n    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}\n    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState • Cloudflare: $cloudflareState"'''
assert old in ms, 'R28 R27 Thoughts anchor missing'
ms=ms.replace(old,new,1)

old='''    var groqKeyInput by remember{mutableStateOf("")}; var groqStatus by remember{mutableStateOf("Checking Groq key status...")}; var cloudStatus by remember{mutableStateOf("Checking cloud provider hierarchy...")}'''
new='''    var groqKeyInput by remember{mutableStateOf("")}; var groqStatus by remember{mutableStateOf("Checking Groq key status...")}; var cloudStatus by remember{mutableStateOf("Checking cloud peer status...")}\n    var cloudflareAccountInput by remember{mutableStateOf("")}; var cloudflareTokenInput by remember{mutableStateOf("")}; var cloudflareStatus by remember{mutableStateOf("Checking Cloudflare credentials...")}'''
assert old in ms, 'R28 AI state anchor missing'
ms=ms.replace(old,new,1)

old='''                val g=repo.groqKeyStatus();groqStatus=g.second.ifBlank{"GROQ_KEY_CONFIGURED=NO"}\n                val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}'''
new='''                val g=repo.groqKeyStatus();groqStatus=g.second.ifBlank{"GROQ_KEY_CONFIGURED=NO"}\n                val cf=repo.cloudflareCredentialsStatus();cloudflareStatus=cf.second.ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"}\n                val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}'''
assert old in ms, 'R28 STATUS anchor missing'
ms=ms.replace(old,new,1)

anchor_ops='''            "GROQ_DELETE"->{val g=repo.deleteGroqKey();groqStatus=g.second;val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CHAT"->{'''
replacement='''            "GROQ_DELETE"->{val g=repo.deleteGroqKey();groqStatus=g.second;val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_STATUS"->{val cf=repo.cloudflareCredentialsStatus();cloudflareStatus=cf.second.ifBlank{"CLOUDFLARE_CREDENTIALS_CONFIGURED=NO"};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_SAVE"->{val cf=repo.saveCloudflareCredentials(cloudflareAccountInput,cloudflareTokenInput);cloudflareStatus=cf.second;if(cf.first){cloudflareAccountInput="";cloudflareTokenInput=""};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CLOUDFLARE_DELETE"->{val cf=repo.deleteCloudflareCredentials();cloudflareStatus=cf.second;val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CHAT"->{'''
assert anchor_ops in ms, 'R28 operation anchor missing'
ms=ms.replace(anchor_ops,replacement,1)

ms=ms.replace('''BoxCard("CLOUD REASONER PRIORITY","Gemini = PRIMARY • Groq = SECONDARY • Local AI = FALLBACK\\n"+cloudStatus,true)''','''BoxCard("CLOUD PEER STATUS","Gemini ⇄ Groq ⇄ Cloudflare • EQUAL • ONE ACTIVE\\nLocal AI = FINAL FALLBACK\\n"+cloudStatus,true)''')

needle='''        OutlinedTextField(value=chatInput,onValueChange={chatInput=it.take(8000)},label={Text("Ask DJAEGER AI")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)'''
assert needle in ms, 'R28 chat anchor missing'
cf_ui='''        BoxCard("CLOUDFLARE CREDENTIAL STATUS",cloudflareStatus,true)\n        OutlinedTextField(value=cloudflareAccountInput,onValueChange={cloudflareAccountInput=it.take(64)},label={Text("Cloudflare Account ID")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        OutlinedTextField(value=cloudflareTokenInput,onValueChange={cloudflareTokenInput=it.take(512)},label={Text("Cloudflare API Token")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={bridgeOp="CLOUDFLARE_SAVE"},enabled=bridgeOp==null&&cloudflareAccountInput.isNotBlank()&&cloudflareTokenInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE / REPLACE")}\n            Button(onClick={bridgeOp="CLOUDFLARE_STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}\n            Button(onClick={bridgeOp="CLOUDFLARE_DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}\n        }\n'''
ms=ms.replace(needle,cf_ui+needle,1)

assert 'CONTROL CENTER • v0.12.1-r28 • THREE EQUAL CLOUD PEERS' in ms
assert 'Gemini, Groq, and Cloudflare are equal cloud peers' in ms
assert 'GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI' in ms
assert 'Cloudflare: $cloudflareState' in ms
assert 'Text("Cloudflare Account ID")' in ms
assert 'Text("Cloudflare API Token")' in ms
assert 'repo.saveCloudflareCredentials(cloudflareAccountInput,cloudflareTokenInput)' in ms
assert '"CLOUDFLARE"->"◇ CLOUDFLARE • $status"' in ms
assert 'Gemini = PRIMARY' not in ms
assert 'Groq = SECONDARY' not in ms
m.write_text(ms)

print('R28_THREE_EQUAL_CLOUD_PEERS_UI=PASS')
print('R28_CLOUDFLARE_CREDENTIALS=ACCOUNT_ID_PLUS_API_TOKEN')
print('R28_CLOUDFLARE_WRITE=STDIN_ONLY')
print('R28_THOUGHTS=GEMINI_GROQ_CLOUDFLARE')
print('R28_LOCAL_AI=FINAL_FALLBACK')
