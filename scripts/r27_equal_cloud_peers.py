#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12270',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r27"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r26 • PROVIDER-AWARE CHAT','CONTROL CENTER • v0.12.1-r27 • EQUAL CLOUD PEERS',1).replace('v0.12.1-r26','v0.12.1-r27')
ms=ms.replace(
    'Ask DJAEGER naturally. Gemini is primary, Groq is secondary, and Local AI is the final fallback.',
    'Ask DJAEGER naturally. Gemini and Groq are equal cloud peers; one peer is active at a time, and Local AI is the final fallback.'
)
old='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI -> GROQ -> LOCAL_AI"}.replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Provider chain: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState"'''
new='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")
    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState"'''
assert old in ms, 'R27 provider-lines anchor missing'
ms=ms.replace(old,new,1)
assert 'Gemini is primary' not in ms
assert 'Groq is secondary' not in ms
assert 'GEMINI <-> GROQ => LOCAL_AI' in ms
assert 'Cloud peers: $relation • ONE ACTIVE' in ms
assert 'Provider selection: $chain' in ms
assert 'CONTROL CENTER • v0.12.1-r27 • EQUAL CLOUD PEERS' in ms
m.write_text(ms)

print('R27_EQUAL_CLOUD_PEERS_UI=PASS')
print('R27_PROVIDER_RELATION=PEER_EQUAL')
print('R27_ONE_ACTIVE_CLOUD=1')
print('R27_LOCAL_AI=FINAL_FALLBACK')
