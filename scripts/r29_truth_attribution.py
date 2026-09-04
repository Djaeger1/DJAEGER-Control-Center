#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12290',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r29"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r28 • THREE EQUAL CLOUD PEERS','CONTROL CENTER • v0.12.1-r29 • TRUTH ATTRIBUTION',1).replace('v0.12.1-r28','v0.12.1-r29')

# The Thoughts writer is authoritative only from the backend-published Thoughts SOURCE.
# Cloud transport/reasoner state is intentionally displayed separately so "Active now"
# can never claim CLOUDFLARE/GEMINI/GROQ when LOCAL_AI actually authored the visible text.
old='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")
    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState • Cloudflare: $cloudflareState"'''
new='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")
    val cloudReasoner=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{"UNKNOWN"}.replace("LOCAL_AI","LOCAL AI")
    val activeCloud=thoughtField(s.providerStatus,"ACTIVE_CLOUD").ifBlank{if(cloudReasoner=="GEMINI"||cloudReasoner=="GROQ"||cloudReasoner=="CLOUDFLARE")cloudReasoner else "NONE"}
    val activeThoughtSource=src.replace("LOCAL_AI","LOCAL AI")
    val strategySource=thoughtField(s.providerStatus,"STRATEGY_SOURCE").ifBlank{"LOCAL_BASELINE"}.replace("LOCAL_AI","LOCAL AI").replace("LOCAL_BASELINE","LOCAL BASELINE")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Active now: $activeThoughtSource\\nCloud active: $activeCloud\\nCloud peers: $relation • ONE ACTIVE\\nRoute: $chain\\nStrategy: $strategySource\\nGemini: $geminiState • Groq: $groqState • Cloudflare: $cloudflareState"'''
assert old in ms, 'R29 R28 provider block missing'
ms=ms.replace(old,new,1)

old_card='''    BoxCard("DJAEGER THOUGHTS • $badge", providerLines+"\\n\\n"+text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)'''
new_card='''    BoxCard("THOUGHTS • $badge", providerLines+"\\n\\n"+text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)'''
assert old_card in ms, 'R29 Thoughts card title anchor missing'
ms=ms.replace(old_card,new_card,1)

old_footer='Transport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.'
new_footer='Cloud transport failures affect only the selected chat peer. Local AI and kernel execution remain independently observable below.'
assert old_footer in ms, 'R29 legacy Gemini-only chat footer missing'
ms=ms.replace(old_footer,new_footer,1)

# Provider-neutralize the human-view card: this content is DJAEGER-published state, not necessarily Gemini.
ms=ms.replace('BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true)','BoxCard("DJAEGER INTELLIGENCE HUMAN VIEW",retained,true)',1)

assert 'CONTROL CENTER • v0.12.1-r29 • TRUTH ATTRIBUTION' in ms
assert 'BoxCard("THOUGHTS • $badge"' in ms
assert 'DJAEGER THOUGHTS' not in ms
assert 'Active now: $activeThoughtSource' in ms
assert 'Cloud active: $activeCloud' in ms
assert 'Route: $chain' in ms
assert 'Strategy: $strategySource' in ms
assert 'activeThoughtSource=src.replace("LOCAL_AI","LOCAL AI")' in ms
assert 'Active reasoner:' not in ms
assert 'Thought source:' not in ms
assert old_footer not in ms
assert new_footer in ms
assert 'DJAEGER INTELLIGENCE HUMAN VIEW' in ms
m.write_text(ms)

print('R29_THOUGHTS_TITLE=THOUGHTS_ONLY')
print('R29_ACTIVE_NOW=BACKEND_THOUGHT_SOURCE')
print('R29_CLOUD_ACTIVE=SEPARATE_TRANSPORT_STATE')
print('R29_PROVIDER_STATUS=COMPACT_TRUTHFUL')
print('R29_CHAT_FOOTER=PROVIDER_NEUTRAL')
