#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r24"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
anchor='    suspend fun geminiChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){'
assert anchor in rs, 'R24 repository anchor missing'
bridge='''    suspend fun groqKeyStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai groq-key-status",5000); Pair(rc==0,out.trim())\n    }\n    suspend fun saveGroqKey(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(key.isBlank()) return@withContext Pair(false,"GROQ_KEY_REJECTED=EMPTY")\n        val (rc,out)=suStdin("djaeger-ai groq-key-stdin",key); Pair(rc==0,out.trim())\n    }\n    suspend fun deleteGroqKey():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai groq-key-delete",5000); Pair(rc==0,out.trim())\n    }\n    suspend fun cloudProviderStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai cloud-provider-status",5000); Pair(rc==0,out.trim())\n    }\n\n'''
assert 'suspend fun groqKeyStatus()' not in rs, 'R24 Groq repository methods already present'
rs=rs.replace(anchor,bridge+anchor,1)
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r23 • GEMINI + GROQ SOURCE','CONTROL CENTER • v0.12.1-r24 • GEMINI + GROQ KEY UI',1).replace('v0.12.1-r23','v0.12.1-r24')

old='''    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}\n    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}'''
new='''    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}\n    var groqKeyInput by remember{mutableStateOf("")}; var groqStatus by remember{mutableStateOf("Checking Groq key status...")}; var cloudStatus by remember{mutableStateOf("Checking cloud provider hierarchy...")}\n    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}'''
assert old in ms, 'R24 AI state anchor missing'
ms=ms.replace(old,new,1)

old_status='''            "STATUS"->{val r=repo.geminiKeyStatus();bridgeStatus=r.second.ifBlank{"KEY_CONFIGURED=NO"}}\n            "SAVE"->{val r=repo.saveGeminiKey(keyInput);bridgeStatus=r.second;if(r.first)keyInput=""}\n            "DELETE"->{val r=repo.deleteGeminiKey();bridgeStatus=r.second}\n            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}'''
new_status='''            "STATUS"->{\n                val r=repo.geminiKeyStatus();bridgeStatus=r.second.ifBlank{"KEY_CONFIGURED=NO"}\n                val g=repo.groqKeyStatus();groqStatus=g.second.ifBlank{"GROQ_KEY_CONFIGURED=NO"}\n                val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}\n            }\n            "SAVE"->{val r=repo.saveGeminiKey(keyInput);bridgeStatus=r.second;if(r.first)keyInput=""}\n            "DELETE"->{val r=repo.deleteGeminiKey();bridgeStatus=r.second}\n            "GROQ_STATUS"->{val g=repo.groqKeyStatus();groqStatus=g.second.ifBlank{"GROQ_KEY_CONFIGURED=NO"};val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "GROQ_SAVE"->{val g=repo.saveGroqKey(groqKeyInput);groqStatus=g.second;if(g.first)groqKeyInput="";val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "GROQ_DELETE"->{val g=repo.deleteGroqKey();groqStatus=g.second;val c=repo.cloudProviderStatus();cloudStatus=c.second.ifBlank{"CLOUD_PROVIDER_STATUS=UNAVAILABLE"}}\n            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}'''
assert old_status in ms, 'R24 bridge operation anchor missing'
ms=ms.replace(old_status,new_status,1)

needle='''        OutlinedTextField(value=chatInput,onValueChange={chatInput=it.take(8000)},label={Text("Ask DJAEGER Gemini")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)'''
assert needle in ms, 'R24 Gemini chat anchor missing'
groq_ui='''        BoxCard("CLOUD REASONER PRIORITY","Gemini = PRIMARY • Groq = SECONDARY • Local AI = FALLBACK\\n"+cloudStatus,true)\n        BoxCard("GROQ KEY STATUS",groqStatus,true)\n        OutlinedTextField(value=groqKeyInput,onValueChange={groqKeyInput=it},label={Text("Groq API key")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n            Button(onClick={bridgeOp="GROQ_SAVE"},enabled=bridgeOp==null&&groqKeyInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE / REPLACE")}\n            Button(onClick={bridgeOp="GROQ_STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}\n            Button(onClick={bridgeOp="GROQ_DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}\n        }\n'''
ms=ms.replace(needle,groq_ui+needle,1)

assert 'Text("Groq API key")' in ms
assert 'repo.saveGroqKey(groqKeyInput)' in ms
assert 'repo.groqKeyStatus()' in ms
assert 'repo.deleteGroqKey()' in ms
assert 'repo.cloudProviderStatus()' in ms
assert 'PasswordVisualTransformation()' in ms
assert '"GROQ"->"◇ GROQ • $status"' in ms
m.write_text(ms)

print('R24_GROQ_KEY_UI=PASS')
print('R24_GROQ_WRITE=STDIN_ONLY')
print('R24_GROQ_STATUS=MASKED_BACKEND_ONLY')
print('R24_PROVIDER_PRIORITY=GEMINI_PRIMARY_GROQ_SECONDARY_LOCAL_FALLBACK')
print('R24_EXECUTOR_AUTHORITY=UNCHANGED')
