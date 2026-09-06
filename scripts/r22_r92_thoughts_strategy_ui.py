#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

# Presentation-only derivative of the proven R22 line for the R92 backend.
# The base branch remains untouched. No backend, sysfs, network or authority code is added.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12221',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui1"',bs,count=1)
b.write_text(bs)

# R92 plan_history.csv contract is:
# epoch,state,score,reason,mode,profile,lmin,lmax,bmin,bmax,gmin,gmax
# Historical R22 parsed c[0] as state, shifting every displayed strategy field by one.
rs=r.read_text()
old='private fun parsePlan(text:String):PlanRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("state,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<12)return null;return PlanRecord(c[0],c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10])}'
new='private fun parsePlan(text:String):PlanRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("epoch,")&&!it.startsWith("state,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<12)return null;return PlanRecord(c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11])}'
assert old in rs, 'R92 plan parser baseline anchor missing'
rs=rs.replace(old,new,1)
r.write_text(rs)

ms=m.read_text()
start=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
end=ms.index('@Composable fun Overview(s:RuntimeState)',start)
replacement=r'''@Composable fun ThoughtsCard(s:RuntimeState){
    val src=thoughtField(s.thoughts,"SOURCE")
    val status=thoughtField(s.thoughts,"STATUS").ifBlank{"WAITING"}
    val conf=thoughtField(s.thoughts,"CONFIDENCE")
    val text=thoughtField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}
    val sourceName=when(src){"GEMINI"->"GEMINI";"LOCAL_AI"->"LOCAL AI";else->"—"}
    val cloudActive=if(src=="GEMINI") "GEMINI" else "NONE"
    val strategySource=when(src){"GEMINI"->"GEMINI";"LOCAL_AI"->"LOCAL_AI";else->"—"}
    val thoughtTitle=when(src){"GEMINI"->"PEMIKIRAN GEMINI";"LOCAL_AI"->"PEMIKIRAN LOCAL AI";else->"PEMIKIRAN DJAEGER"}
    val memUsed=thoughtField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=thoughtField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=thoughtField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=thoughtField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Active now: $sourceName\nCloud active: $cloudActive\nStrategy: $strategySource\n\n$thoughtTitle • $status\n$text\n\nConfidence: "+(conf.ifBlank{"—"})+"%\n"+mem
    BoxCard("THOUGHTS",body,true)
}

private fun planRange(a:String,b:String,unit:String):String{
    val x=a.trim(); val y=b.trim()
    return if(x.isBlank()||y.isBlank()||x.equals("NA",true)||y.equals("NA",true)) "—" else "$x-$y $unit"
}

@Composable fun StrategyCard(s:RuntimeState){
    val p=s.latestPlan
    val d=s.latestDecision
    val control=p?.mode?.takeIf{it.isNotBlank()&&!it.equals("NA",true)}?:"—"
    val profile=p?.profile?.takeIf{it.isNotBlank()&&!it.equals("NA",true)}?:s.telemetry.profile.takeIf{it.isNotBlank()&&!it.equals("NA",true)}?:"—"
    val state=p?.state?.takeIf{it.isNotBlank()}?:"—"
    val score=p?.score?.takeIf{it.isNotBlank()}?:"—"
    val reason=p?.reason?.takeIf{it.isNotBlank()}?:"—"
    val predFps=d?.predFps?.takeIf{it.isNotBlank()&&!it.equals("NA",true)}?:"Belum tersedia"
    val predSkin=d?.predSkin?.takeIf{it.isNotBlank()&&!it.equals("NA",true)}?:"Belum tersedia"
    val validation=if(p!=null) "$state score=$score: $reason" else "—"
    val body="Keputusan: $control\nProfil / mode: $profile / $control\nUser mode: ${s.userMode}\nPlan state: $state\nCPU little: ${if(p==null) "—" else planRange(p.lmin,p.lmax,"kHz")}\nCPU big: ${if(p==null) "—" else planRange(p.bmin,p.bmax,"kHz")}\nGPU: ${if(p==null) "—" else planRange(p.gmin,p.gmax,"MHz")}\nPrediksi FPS: $predFps\nPrediksi skin: $predSkin\nRisiko: Belum tersedia\nConfidence: ${if(score=="—") "—" else "$score%"}\nReview ulang: —\nValidasi Local AI: $validation"
    BoxCard("STRATEGI",body,true)
}

'''
ms=ms[:start]+replacement+ms[end:]

needle='StatusCard(s);ThoughtsCard(s);Row(Modifier.fillMaxWidth()'
assert needle in ms, 'R92 Overview card insertion anchor missing'
ms=ms.replace(needle,'StatusCard(s);ThoughtsCard(s);StrategyCard(s);Row(Modifier.fillMaxWidth()',1)

# Visible provenance label only; no authority change.
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r22-r92ui1 • R92 THOUGHTS + STRATEGY',1)

# Guard against accidental provider expansion or direct write authority.
assert 'GROQ' not in replacement and 'CLOUDFLARE' not in replacement
assert '/sys/' not in replacement
assert 'su(' not in replacement
assert 'ProcessBuilder' not in replacement
assert 'StrategyCard(s)' in ms
assert 'Active now:' in ms and 'Cloud active:' in ms and 'PEMIKIRAN GEMINI' in ms
assert 'return PlanRecord(c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11])' in r.read_text()

m.write_text(ms)

print('R92_UI1_BASELINE=R22')
print('R92_UI1_PLAN_PARSER=EPOCH_SHIFT_FIXED')
print('R92_UI1_THOUGHTS=SOURCE_TRUTH_ONLY')
print('R92_UI1_STRATEGY=TYPED_PLAN_HISTORY')
print('R92_UI1_BACKEND_CHANGE=NONE')
print('R92_UI1_PROVIDER_EXPANSION=NONE')
