#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12222',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui2"',bs,count=1)
b.write_text(bs)

# Module r92-fix2 publishes validated strategy transparency in the same atomic cc_snapshot.
cs=mapper.read_text()
assert 'val memoryStatus: String,' in cs
cs=cs.replace('val memoryStatus: String,','val memoryStatus: String,\n        val strategyResult: String,',1)
assert 'memoryStatus = s["MEMORY"].orEmpty(),' in cs
cs=cs.replace('memoryStatus = s["MEMORY"].orEmpty(),','memoryStatus = s["MEMORY"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),',1)
mapper.write_text(cs)

rs=r.read_text()
assert 'val memoryStatus:String=""' in rs
rs=rs.replace('val memoryStatus:String=""','val memoryStatus:String="",val strategyResult:String=""',1)
assert 'memoryStatus=mapped.memoryStatus,' in rs
rs=rs.replace('memoryStatus=mapped.memoryStatus,','memoryStatus=mapped.memoryStatus,strategyResult=mapped.strategyResult,',1)
r.write_text(rs)

ms=m.read_text()
start=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
end=ms.index('@Composable fun Overview(s:RuntimeState)', start)
replacement=r'''private fun envField(raw:String,key:String):String = thoughtField(raw,key)
private fun effectiveSourceLabel(raw:String,active:String):String{
    if(active!="1") return "IDLE"
    return when(raw){
        "GEMINI"->"GEMINI"
        "LOCAL_LEARNED","LOCAL_BASELINE","USER_MODE_OFFLINE","LOCAL_FRAME","VALIDATOR_FALLBACK","RESCUE_GUARD"->"LOCAL AI"
        else->if(raw.startsWith("LOCAL")) "LOCAL AI" else "—"
    }
}

@Composable fun ThoughtsCard(s:RuntimeState){
    val execSource=envField(s.brain,"SOURCE")
    val activeNow=effectiveSourceLabel(execSource,s.active)
    val cloudActive=if(s.active=="1"&&execSource=="GEMINI") "GEMINI" else "NONE"
    val strategy=when(activeNow){"GEMINI"->"GEMINI";"LOCAL AI"->"LOCAL_AI";"IDLE"->"IDLE";else->"—"}
    val thoughtSrc=envField(s.thoughts,"SOURCE")
    val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
    val conf=envField(s.thoughts,"CONFIDENCE")
    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}
    val thoughtTitle=when(thoughtSrc){"GEMINI"->"PEMIKIRAN GEMINI";"LOCAL_AI"->"PEMIKIRAN LOCAL AI";else->"PEMIKIRAN DJAEGER"}
    val memUsed=envField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=envField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=envField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=envField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Active now: $activeNow\nCloud active: $cloudActive\nStrategy: $strategy\nEffective source: "+(execSource.ifBlank{"—"})+"\n\n$thoughtTitle • $thoughtStatus\n$text\n\nThought source: "+(thoughtSrc.ifBlank{"—"})+"\nConfidence: "+(conf.ifBlank{"—"})+"%\n"+mem
    BoxCard("THOUGHTS",body,true)
}

private fun currentRange(raw:String,unit:String):String{
    val v=raw.trim()
    return if(v.isBlank()||v.contains("NA")) "—" else "$v $unit"
}

private fun planRange(a:String,b:String,unit:String):String{
    val x=a.trim(); val y=b.trim()
    return if(x.isBlank()||y.isBlank()||x.equals("NA",true)||y.equals("NA",true)) "—" else "$x-$y $unit"
}

@Composable fun StrategyCard(s:RuntimeState){
    val src=envField(s.brain,"SOURCE")
    val cloudAction=envField(s.brain,"MODE")
    val finalProfile=envField(s.brain,"FINAL_PROFILE")
    val execMode=envField(s.brain,"EXEC_MODE")
    val little=envField(s.brain,"EXEC_LITTLE")
    val big=envField(s.brain,"EXEC_BIG")
    val gpu=envField(s.brain,"EXEC_GPU")
    val shadowState=envField(s.brain,"SHADOW_STATE")
    val shadowScore=envField(s.brain,"SHADOW_SCORE")
    val shadowReason=envField(s.brain,"SHADOW_REASON")
    val learnedState=envField(s.brain,"LEARNED_STATE")
    val updated=envField(s.brain,"UPDATED_AT")

    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val srUpdated=envField(s.strategyResult,"RESULT_UPDATED_AT")
    val srPipeline=if(s.strategyResult.isNotBlank()) "VALIDATED SNAPSHOT" else "UNAVAILABLE / LOCAL PATH"

    val p=s.latestPlan
    val usingBrain=finalProfile.isNotBlank()||execMode.isNotBlank()||src.isNotBlank()
    val profile=if(usingBrain) finalProfile.ifBlank{s.telemetry.profile} else p?.profile?:s.telemetry.profile
    val mode=if(usingBrain) execMode.ifBlank{"PROFILE"} else p?.mode?:"—"
    val decision=if(usingBrain) cloudAction.ifBlank{mode} else p?.mode?:"—"
    val validation=when{
        srValidation.isNotBlank()->"$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}"
        shadowState.isNotBlank()->"$shadowState score=${shadowScore.ifBlank{"—"}}: ${shadowReason.ifBlank{"—"}}"
        learnedState.isNotBlank()->learnedState
        else->"—"
    }
    val truth=if(usingBrain) "CURRENT BRAIN / FUSED" else "HISTORICAL FALLBACK"
    val body="Truth: $truth\nKeputusan: $decision\nProfil / mode: $profile / $mode\nUser mode: ${s.userMode}\nEffective source: ${src.ifBlank{"—"}}\nCPU little: ${if(usingBrain) currentRange(little,"kHz") else if(p!=null) planRange(p.lmin,p.lmax,"kHz") else "—"}\nCPU big: ${if(usingBrain) currentRange(big,"kHz") else if(p!=null) planRange(p.bmin,p.bmax,"kHz") else "—"}\nGPU: ${if(usingBrain) currentRange(gpu,"MHz") else if(p!=null) planRange(p.gmin,p.gmax,"MHz") else "—"}\nPlan state: ${shadowState.ifBlank{p?.state?:"—"}}\nConfidence: ${shadowScore.ifBlank{p?.score?:"—"}}%\nReason: ${shadowReason.ifBlank{p?.reason?:"—"}}\nValidasi Local AI: $validation\nStrategy result: $srPipeline\nBrain updated: ${updated.ifBlank{"—"}} • Strategy updated: ${srUpdated.ifBlank{"—"}}"
    BoxCard("STRATEGI",body,true)
}

'''
ms=ms[:start]+replacement+ms[end:]
ms=ms.replace('CONTROL CENTER • v0.12.1-r22-r92ui1 • R92 THOUGHTS + STRATEGY','CONTROL CENTER • v0.12.1-r22-r92ui2 • R92 MODULE-SYNC TRUTH',1)
assert 'Active now: $activeNow' in ms
assert 'Truth: $truth' in ms
assert 's.strategyResult' in ms
assert 'GROQ' not in replacement and 'CLOUDFLARE' not in replacement
assert '/sys/' not in replacement and 'ProcessBuilder' not in replacement
m.write_text(ms)

print('R92_UI2_BASELINE=R22_PLUS_UI1')
print('R92_UI2_PRIMARY_TRUTH=BRAIN_FUSED_CURRENT')
print('R92_UI2_STRATEGY_RESULT=ATOMIC_CC_SNAPSHOT')
print('R92_UI2_PLAN_HISTORY=FALLBACK_ONLY')
print('R92_UI2_PROVIDER_SCOPE=GEMINI_LOCAL_ONLY')
