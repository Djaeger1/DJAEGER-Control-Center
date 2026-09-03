#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12230',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r23"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# r115 publishes one atomic app-facing truth file. Read it in the same root snapshot as telemetry.
needle="        echo __BRAIN__;"
assert needle in rs
rs=rs.replace(needle,"        echo __CCSYNC__; cat '$persistent/cc_sync.env' 2>/dev/null\n"+needle,1)
# Do not let CCSYNC lines pollute direct live sysfs parsing.
rs=rs.replace('section("LIVE","BRAIN")','section("LIVE","CCSYNC")')
# Parse canonical contract once; prefer it over legacy runtime_status aliases.
anchor='        fun maxTemp(test:(String)->Boolean):Int=TelemetryNormalizer.maxThermal(thermals,test)'
assert anchor in rs
rs=rs.replace(anchor,'        val sync=section("CCSYNC","BRAIN").lineSequence().mapNotNull{line-> val p=line.indexOf(\'=\'); if(p<=0)null else line.substring(0,p).trim() to line.substring(p+1).trim().trim().trim(\'\\\'\')}.toMap()\n'+anchor,1)
# Strategy truth in r22 is assembled from plan/decision history. Override each app-facing field with
# canonical current r115 truth when present, while retaining history only as compatibility fallback.
insert_anchor='        val strategy=StrategyTruth('
assert insert_anchor in rs
rs=rs.replace(insert_anchor,'        fun sv(key:String,fallback:String):String=sync[key]?.takeIf{it.isNotBlank()&&it!="NA"}?:fallback\n'+insert_anchor,1)
# Rewrite StrategyTruth assignments individually so this generator is resilient to prior r15/r16 formatting.
repls={
'source=rv("DECISION_SOURCE","decision_source","SOURCE").let{if(it=="—") rv("SOURCE") else it},':'source=sv("DECISION_SOURCE",rv("DECISION_SOURCE","decision_source","SOURCE").let{if(it=="—") rv("SOURCE") else it}),',
'proposal=plan?.let{"${it.state} ${it.mode} ${it.profile}"}?:"UNAVAILABLE",':'proposal=sv("PROPOSED",plan?.let{"${it.state} ${it.mode} ${it.profile}"}?:"UNAVAILABLE"),',
'validation=plan?.let{"${it.state}: ${it.reason}"}?:"UNAVAILABLE",':'validation=sv("VALIDATION",plan?.let{"${it.state}: ${it.reason}"}?:"UNAVAILABLE"),',
'applied="UNAVAILABLE — requires fresh __EXECUTION__",':'applied=sv("APPLIED","UNAVAILABLE — requires fresh __EXECUTION__"),',
'readback="UNAVAILABLE — no verified readback evidence",':'readback=sv("READBACK","UNAVAILABLE — no verified readback evidence"),',
'outcome=dec?.outcome?:"UNAVAILABLE",':'outcome=sv("OUTCOME",dec?.outcome?:"UNAVAILABLE"),',
'cpuLittleMin=plan?.lmin?:"—",cpuLittleMax=plan?.lmax?:"—",cpuBigMin=plan?.bmin?:"—",cpuBigMax=plan?.bmax?:"—",gpuMin=plan?.gmin?:"—",gpuMax=plan?.gmax?:"—",':'cpuLittleMin=sv("CPU_LITTLE_MIN",plan?.lmin?:"—"),cpuLittleMax=sv("CPU_LITTLE_MAX",plan?.lmax?:"—"),cpuBigMin=sv("CPU_BIG_MIN",plan?.bmin?:"—"),cpuBigMax=sv("CPU_BIG_MAX",plan?.bmax?:"—"),gpuMin=sv("GPU_MIN",plan?.gmin?:"—"),gpuMax=sv("GPU_MAX",plan?.gmax?:"—"),',
'confidence=plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE"),':'confidence=sv("CONFIDENCE",plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE")),',
'rationale=plan?.reason?:rv("STRATEGY_RATIONALE","RATIONALE"),':'rationale=sv("RATIONALE",plan?.reason?:rv("STRATEGY_RATIONALE","RATIONALE")),',
'learningSamples=rv("LEARNING_SAMPLES","SAMPLES"),learningConfidence=rv("LEARNING_CONFIDENCE","CONFIDENCE"),learningPromotion=rv("LEARNED_STATE","LEARNING_STATUS"))':'learningSamples=sv("LEARNING_SAMPLES",rv("LEARNING_SAMPLES","SAMPLES")),learningConfidence=sv("LEARNING_CONFIDENCE",rv("LEARNING_CONFIDENCE","CONFIDENCE")),learningPromotion=sv("LEARNING_PROMOTION",rv("LEARNED_STATE","LEARNING_STATUS")))'
}
for old,new in repls.items():
    if old in rs: rs=rs.replace(old,new,1)
# Canonical profile follows current module contract.
rs=rs.replace('profile=frameParts.getOrNull(1)?:tel.profile','profile=sync["PROFILE"]?.takeIf{it.isNotBlank()&&it!="NA"}?:frameParts.getOrNull(1)?:tel.profile',1)
# Fill governor/comfort fields that legacy history did not provide.
needle2='            confidence=sv("CONFIDENCE",plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE")),'
if needle2 in rs:
    rs=rs.replace(needle2,'            cpuGovernor=sv("CPU_GOVERNOR","—"),gpuGovernor=sv("GPU_GOVERNOR","—"),comfortCeiling=sv("COMFORT_CEILING","—"),\n'+needle2,1)
r.write_text(rs)
ms=m.read_text()
# User requested these internal-only panels removed from app UI. Backend safety/authority remain intact.
ms=re.sub(r'\s*BoxCard\("KERNEL AUTHORITY",s\.authority\.ifBlank\{"UNAVAILABLE — authority state not published\."\},true\)','',ms)
ms=re.sub(r'\s*BoxCard\("SESSION SAFETY",\(s\.sessionSafety\+"\\n"\+s\.supervisor\)\.trim\(\)\.ifBlank\{"UNAVAILABLE — session safety state not published\."\},true\)','',ms)
ms=ms.replace('BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)','')
ms=ms.replace('BoxCard("SESSION SAFETY",(s.sessionSafety+"\\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)','')
ms=ms.replace('CONTROL CENTER • v0.12.1-r22 • GEMINI-FIRST THOUGHTS','CONTROL CENTER • v0.12.1-r23 • MATCHED MODULE SYNC')
m.write_text(ms)
print('R23_CC_SYNC=DJAEGER_CC_SYNC_V2')
print('R23_INTERNAL_PANELS=REMOVED_FROM_UI_ONLY')
print('R23_SYSFS_AUTHORITY=READ_ONLY_UNCHANGED')
