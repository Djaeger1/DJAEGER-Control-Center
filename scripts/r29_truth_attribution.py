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

# Keep the Thoughts card intentionally minimal, while every attribution line is
# derived from backend-published truth rather than a UI guess.
#
# Active now = all AI actors that are BOTH online and standing by/usable.
# Local AI requires a live published predictor PID plus a published Local-AI role.
# Cloud actors require READY or ACTIVE provider state.
#
# Cloud active = every cloud provider whose published state is ACTIVE. Do not
# collapse multiple simultaneously ACTIVE cloud states into one display value.
# ACTIVE_REASONER is only a compatibility fallback when no provider publishes
# an ACTIVE state.
#
# Strategy = module-published strategy/decision source. Transport availability
# must never be substituted for strategy authorship.
old='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")
    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState • Cloudflare: $cloudflareState"'''
new='''    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val localRole=thoughtField(s.providerStatus,"LOCAL_AI_ROLE").uppercase()
    val cloudReasoner=thoughtField(s.providerStatus,"ACTIVE_REASONER").uppercase()

    val localOnline=s.predictorPid.isNotBlank() && s.predictorPid!="0" && localRole.isNotBlank() && localRole!="NONE" && localRole!="UNAVAILABLE"
    val standbyActors=mutableListOf<String>()
    if(localOnline) standbyActors.add("LOCAL AI")
    if(geminiState=="READY" || geminiState=="ACTIVE") standbyActors.add("GEMINI")
    if(groqState=="READY" || groqState=="ACTIVE") standbyActors.add("GROQ")
    if(cloudflareState=="READY" || cloudflareState=="ACTIVE") standbyActors.add("CLOUDFLARE")
    val activeNow=standbyActors.distinct().joinToString(" • ").ifBlank{"NONE"}

    val activeCloudActors=mutableListOf<String>()
    if(geminiState=="ACTIVE") activeCloudActors.add("GEMINI")
    if(groqState=="ACTIVE") activeCloudActors.add("GROQ")
    if(cloudflareState=="ACTIVE") activeCloudActors.add("CLOUDFLARE")
    if(activeCloudActors.isEmpty() && (cloudReasoner=="GEMINI" || cloudReasoner=="GROQ" || cloudReasoner=="CLOUDFLARE")) activeCloudActors.add(cloudReasoner)
    val activeCloud=activeCloudActors.distinct().joinToString(" • ").ifBlank{"NONE"}

    val strategyRaw=s.strategy.source.trim()
    val strategySource=when(strategyRaw.uppercase()){
        "LOCAL_AI","LOCAL AI","LOCAL_BASELINE","LOCAL BASELINE","LOCAL"->"LOCAL AI"
        "GEMINI"->"GEMINI"
        "GROQ"->"GROQ"
        "CLOUDFLARE"->"CLOUDFLARE"
        "","—","UNAVAILABLE","UNKNOWN","NA"->"UNAVAILABLE"
        else->strategyRaw.replace("_"," ")
    }
    val providerLines="Active now: $activeNow\\nCloud active: $activeCloud\\nStrategy: $strategySource"'''
assert old in ms, 'R29 R28 provider block missing'
ms=ms.replace(old,new,1)

old_card='''    BoxCard("DJAEGER THOUGHTS • $badge", providerLines+"\\n\\n"+text+"\\n\\nConfidence: "+(conf.ifBlank{"—"})+"%\\n"+mem, true)'''
new_card='''    BoxCard("THOUGHTS", providerLines+"\\n\\n"+text, true)'''
assert old_card in ms, 'R29 Thoughts card title anchor missing'
ms=ms.replace(old_card,new_card,1)

old_footer='Transport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.'
new_footer='Cloud transport failures affect only the selected chat peer. Local AI and kernel execution remain independently observable below.'
assert old_footer in ms, 'R29 legacy Gemini-only chat footer missing'
ms=ms.replace(old_footer,new_footer,1)

ms=ms.replace('BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true)','BoxCard("DJAEGER INTELLIGENCE HUMAN VIEW",retained,true)',1)

assert 'CONTROL CENTER • v0.12.1-r29 • TRUTH ATTRIBUTION' in ms
assert 'BoxCard("THOUGHTS", providerLines+"\\n\\n"+text, true)' in ms
assert 'DJAEGER THOUGHTS' not in ms
assert 'val providerLines="Active now: $activeNow\\nCloud active: $activeCloud\\nStrategy: $strategySource"' in ms
assert 'val localOnline=s.predictorPid.isNotBlank()' in ms
assert 'if(localOnline) standbyActors.add("LOCAL AI")' in ms
assert 'geminiState=="READY" || geminiState=="ACTIVE"' in ms
assert 'groqState=="READY" || groqState=="ACTIVE"' in ms
assert 'cloudflareState=="READY" || cloudflareState=="ACTIVE"' in ms
assert 'if(geminiState=="ACTIVE") activeCloudActors.add("GEMINI")' in ms
assert 'if(groqState=="ACTIVE") activeCloudActors.add("GROQ")' in ms
assert 'if(cloudflareState=="ACTIVE") activeCloudActors.add("CLOUDFLARE")' in ms
assert 'val strategyRaw=s.strategy.source.trim()' in ms
assert '"LOCAL_AI","LOCAL AI","LOCAL_BASELINE","LOCAL BASELINE","LOCAL"->"LOCAL AI"' in ms
assert 'Active reasoner:' not in ms
assert 'Thought source:' not in ms
assert old_footer not in ms
assert new_footer in ms
assert 'DJAEGER INTELLIGENCE HUMAN VIEW' in ms
m.write_text(ms)

print('R29_THOUGHTS_TITLE=MINIMAL')
print('R29_ACTIVE_NOW=ALL_ONLINE_STANDBY_ACTORS')
print('R29_LOCAL_AI_ONLINE=LIVE_PREDICTOR_PLUS_ROLE')
print('R29_CLOUD_ACTIVE=ALL_BACKEND_ACTIVE_CLOUDS')
print('R29_STRATEGY=MODULE_PUBLISHED_STRATEGY_AUTHOR')
print('R29_MULTI_ACTIVE_CLOUD_DISPLAY=SUPPORTED')
print('R29_THOUGHTS_AUX_LINES=REMOVED')
print('R29_THOUGHTS_CONFIDENCE_MEMORY=REMOVED_FROM_CARD')
