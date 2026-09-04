#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12290',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r29"',bs,count=1)
b.write_text(bs)

# Expose the already-atomic __ATTRIBUTION__ section to RuntimeState.
# No new root read is added: ConsolidatedRuntimeMapper already maps mapped.attribution
# from the same cc_snapshot used by the recurring UI snapshot.
rs=r.read_text()
assert 'val providerStatus:String=""' in rs, 'R29 providerStatus RuntimeState anchor missing'
if 'val attributionStatus:String=""' not in rs:
    rs=rs.replace('val providerStatus:String=""','val providerStatus:String="",val attributionStatus:String=""',1)
assert 'providerStatus=mapped.providerStatus,' in rs, 'R29 providerStatus mapping anchor missing'
if 'attributionStatus=mapped.attribution,' not in rs:
    rs=rs.replace('providerStatus=mapped.providerStatus,','providerStatus=mapped.providerStatus,\n            attributionStatus=mapped.attribution,',1)
assert 'attributionStatus=mapped.attribution,' in rs
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r28 • THREE EQUAL CLOUD PEERS','CONTROL CENTER • v0.12.1-r29 • TRUTH ATTRIBUTION',1).replace('v0.12.1-r28','v0.12.1-r29')

# THOUGHTS semantics:
# - Active now: ONE actor only. It is the actor that is actually active/eligible
#   to own the next Thoughts update. READY alone is not considered active.
#   CLOUD_OFFLINE_OR_STALE explicitly hands ownership to Local AI.
# - Cloud active: ONLY cloud peers whose backend-published state is ACTIVE.
#   READY means available/standby, not active. If multiple peers are genuinely
#   published ACTIVE, show all of them rather than hiding the inconsistency.
# - Strategy: the actual reasoner source from fresh execution attribution when a
#   game session is active. If unavailable/stale, fall back to module-published
#   StrategyTruth, then current Thoughts source, then Local AI.
old='''    val chain=thoughtField(s.providerStatus,"PROVIDER_CHAIN").ifBlank{"GEMINI <-> GROQ <-> CLOUDFLARE => LOCAL_AI"}.replace("<->","⇄").replace("=>","⇒").replace("->","→").replace("LOCAL_AI","LOCAL AI")
    val relation=thoughtField(s.providerStatus,"PROVIDER_RELATION").ifBlank{"PEER_EQUAL"}.replace("PEER_EQUAL","EQUAL")
    val active=thoughtField(s.providerStatus,"ACTIVE_REASONER").ifBlank{src}.replace("LOCAL_AI","LOCAL AI")
    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}
    val providerLines="Cloud peers: $relation • ONE ACTIVE\\nProvider selection: $chain\\nActive now: $active\\nGemini: $geminiState • Groq: $groqState • Cloudflare: $cloudflareState"'''
new='''    fun actorName(raw:String):String=when(raw.trim().uppercase().replace(" ","_")){
        "LOCAL_AI","LOCAL_BASELINE","LOCAL"->"LOCAL AI"
        "GEMINI"->"GEMINI"
        "GROQ"->"GROQ"
        "CLOUDFLARE"->"CLOUDFLARE"
        else->"NONE"
    }
    fun cloudIsActive(state:String)=state=="ACTIVE"
    fun localIsReady(state:String)=state=="READY" || state=="ACTIVE"

    val geminiState=thoughtField(s.providerStatus,"GEMINI_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val groqState=thoughtField(s.providerStatus,"GROQ_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val cloudflareState=thoughtField(s.providerStatus,"CLOUDFLARE_STATUS").ifBlank{"UNKNOWN"}.uppercase()
    val localState=thoughtField(s.providerStatus,"LOCAL_AI_STATUS").ifBlank{"READY"}.uppercase()

    val localOnline=s.predictorPid.isNotBlank() && s.predictorPid!="0" && localIsReady(localState)
    fun actorIsActive(actor:String)=when(actor){
        "GEMINI"->cloudIsActive(geminiState)
        "GROQ"->cloudIsActive(groqState)
        "CLOUDFLARE"->cloudIsActive(cloudflareState)
        "LOCAL AI"->localOnline
        else->false
    }

    val thoughtSource=actorName(src)
    val selectedReasoner=actorName(thoughtField(s.providerStatus,"ACTIVE_REASONER"))
    val thoughtStatus=status.uppercase()
    val cloudStale=thoughtStatus.contains("CLOUD_OFFLINE") || thoughtStatus.contains("CLOUD_STALE") || thoughtStatus.contains("CLOUD_OFFLINE_OR_STALE")
    val activeNow=when{
        cloudStale && localOnline->"LOCAL AI"
        actorIsActive(selectedReasoner)->selectedReasoner
        actorIsActive(thoughtSource)->thoughtSource
        localOnline->"LOCAL AI"
        else->"NONE"
    }

    val cloudActors=mutableListOf<String>()
    if(cloudIsActive(geminiState)) cloudActors.add("GEMINI")
    if(cloudIsActive(groqState)) cloudActors.add("GROQ")
    if(cloudIsActive(cloudflareState)) cloudActors.add("CLOUDFLARE")
    val activeCloud=cloudActors.joinToString(" • ").ifBlank{"NONE"}

    val nowEpoch=System.currentTimeMillis()/1000
    val attributionAt=thoughtField(s.attributionStatus,"UPDATED_AT").toLongOrNull()?:0L
    val attributionFresh=attributionAt>0 && (nowEpoch-attributionAt) in 0..1200
    val attributionSource=actorName(thoughtField(s.attributionStatus,"REASONER_SOURCE"))
    val publishedStrategySource=actorName(s.strategy.source)
    val strategySource=when{
        s.active=="1" && attributionFresh && attributionSource!="NONE"->attributionSource
        s.active=="1" && publishedStrategySource!="NONE"->publishedStrategySource
        s.active=="1" && thoughtSource!="NONE"->thoughtSource
        localOnline->"LOCAL AI"
        else->"NONE"
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
assert 'fun cloudIsActive(state:String)=state=="ACTIVE"' in ms
assert 'val activeNow=when{' in ms
assert 'actorIsActive(selectedReasoner)->selectedReasoner' in ms
assert 'actorIsActive(thoughtSource)->thoughtSource' in ms
assert 'val cloudActors=mutableListOf<String>()' in ms
assert 'if(cloudIsActive(geminiState)) cloudActors.add("GEMINI")' in ms
assert 'if(cloudIsActive(groqState)) cloudActors.add("GROQ")' in ms
assert 'if(cloudIsActive(cloudflareState)) cloudActors.add("CLOUDFLARE")' in ms
assert 'READY alone is not considered active.' in open(__file__).read() if False else True
assert 'val attributionSource=actorName(thoughtField(s.attributionStatus,"REASONER_SOURCE"))' in ms
assert 's.active=="1" && attributionFresh && attributionSource!="NONE"' in ms
assert 'standbyActors' not in ms
assert 'Active reasoner:' not in ms
assert 'Thought source:' not in ms
assert old_footer not in ms
assert new_footer in ms
assert 'DJAEGER INTELLIGENCE HUMAN VIEW' in ms
m.write_text(ms)

print('R29_THOUGHTS_TITLE=MINIMAL')
print('R29_ACTIVE_NOW=ONE_ACTUALLY_ACTIVE_CANDIDATE')
print('R29_READY_NOT_ACTIVE=ENFORCED')
print('R29_ACTIVE_NOW_CLOUD_STALE=LOCAL_AI')
print('R29_CLOUD_ACTIVE=ACTIVE_ONLY_NOT_READY')
print('R29_MULTI_ACTIVE_CLOUD_DISPLAY=SUPPORTED')
print('R29_STRATEGY=FRESH_ATTRIBUTION_REASONER_SOURCE')
print('R29_ATTRIBUTION=ATOMIC_CC_SNAPSHOT_NO_EXTRA_ROOT_READ')
print('R29_THOUGHTS_CONFIDENCE_MEMORY=REMOVED_FROM_CARD')
