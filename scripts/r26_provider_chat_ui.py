#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12260',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r26"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
old='''    suspend fun geminiChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(prompt.isBlank()) return@withContext Pair(false,"CHAT_ERROR=EMPTY_PROMPT")\n        val (rc,out)=suStdin("djaeger-ai gemini-chat-stdin",prompt.take(8000)); Pair(rc==0,out.trim())\n    }\n\n    suspend fun geminiKnowledgeStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){'''
new='''    suspend fun djaegerChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(prompt.isBlank()) return@withContext Pair(false,"CHAT_ERROR=EMPTY_PROMPT")\n        val (rc,out)=suStdin("djaeger-ai chat-stdin",prompt.take(8000)); Pair(rc==0,out.trim())\n    }\n    suspend fun djaegerChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai chat-clear",5000); Pair(rc==0,out.trim())\n    }\n\n    suspend fun geminiKnowledgeStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){'''
assert old in rs, 'R26 repository chat anchor missing'
rs=rs.replace(old,new,1)
# Remove the legacy clear method to avoid the UI accidentally calling the Gemini-only clear command.
rs=rs.replace('''    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai gemini-chat-clear",5000); Pair(rc==0,out.trim())\n    }\n\n''','',1)
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r25 • LIVE PROVIDER CHAIN','CONTROL CENTER • v0.12.1-r26 • PROVIDER-AWARE CHAT',1).replace('v0.12.1-r25','v0.12.1-r26')
ms=ms.replace('Ask Gemini naturally. DJAEGER will provide relevant device context when available.','Ask DJAEGER naturally. Gemini is primary, Groq is secondary, and Local AI is the final fallback.')
ms=ms.replace('repo.geminiChat(chatInput)','repo.djaegerChat(chatInput)')
ms=ms.replace('repo.geminiChatClear()','repo.djaegerChatClear()')
ms=ms.replace('Text("Ask DJAEGER Gemini")','Text("Ask DJAEGER AI")')
ms=ms.replace('Text("ASK GEMINI")','Text("ASK DJAEGER")')
ms=ms.replace('BoxCard("GEMINI CONVERSATION"','BoxCard("DJAEGER CONVERSATION"')
assert 'Text("Ask DJAEGER AI")' in ms
assert 'Text("ASK DJAEGER")' in ms
assert 'DJAEGER CONVERSATION' in ms
assert 'repo.djaegerChat(chatInput)' in ms
assert 'repo.djaegerChatClear()' in ms
assert 'Ask DJAEGER Gemini' not in ms
assert 'ASK GEMINI' not in ms
m.write_text(ms)

print('R26_PROVIDER_CHAT_UI=PASS')
print('R26_CHAT_COMMAND=djaeger-ai_chat-stdin')
print('R26_CHAT_CHAIN=GEMINI_TO_GROQ_TO_LOCAL_AI')
print('R26_SECRET_HANDLING=STDIN_ONLY')
