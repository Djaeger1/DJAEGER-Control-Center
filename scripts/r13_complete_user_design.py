#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12130',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r13"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Typed read-only strategy truth. Values are accepted only from cc_snapshot RUNTIME keys published by DJAEGER.
if 'data class StrategyTruth(' not in rs:
    anchor='data class RuntimeState('
    i=rs.index(anchor)
    model='''data class StrategyTruth(val source:String="UNAVAILABLE",val proposal:String="UNAVAILABLE",val validation:String="UNAVAILABLE",val applied:String="UNAVAILABLE",val readback:String="UNAVAILABLE",val outcome:String="UNAVAILABLE",val cpuLittleMin:String="—",val cpuLittleMax:String="—",val cpuBigMin:String="—",val cpuBigMax:String="—",val gpuMin:String="—",val gpuMax:String="—",val cpuGovernor:String="—",val gpuGovernor:String="—",val powerBias:String="—",val burstLease:String="—",val comfortCeiling:String="—",val confidence:String="—",val rationale:String="Not published by current DJAEGER module",val fpsOutcome:String="—",val frameOutcome:String="—",val thermalOutcome:String="—",val powerOutcome:String="—",val learningSamples:String="—",val learningConfidence:String="—",val learningPromotion:String="—")\n\n'''
    rs=rs[:i]+model+rs[i:]
# Add StrategyTruth to RuntimeState declaration.
mt=re.search(r'^data class RuntimeState\((.*)\)$',rs,re.MULTILINE)
if not mt: raise SystemExit('R13_FAIL=RuntimeState')
decl=mt.group(0)
if 'val strategy:StrategyTruth' not in decl:
    patched=decl[:-1]+',val strategy:StrategyTruth=StrategyTruth())'
    rs=rs[:mt.start()]+patched+rs[mt.end():]
# Map only module-published RUNTIME keys; never derive clocks.
needle='        RuntimeState(\n            root=true,'
if needle not in rs: raise SystemExit('R13_FAIL=snapshot-runtime')
truth='''        fun rv(vararg k:String):String{k.forEach{if(!rt[it].isNullOrBlank())return rt[it]!!};return "—"}\n        val strategy=StrategyTruth(\n            source=rv("DECISION_SOURCE","decision_source","SOURCE"), proposal=rv("PIPELINE_PROPOSED","PROPOSED"), validation=rv("PIPELINE_VALIDATION","VALIDATION_STATUS"), applied=rv("PIPELINE_APPLIED","APPLIED_STATUS"), readback=rv("PIPELINE_READBACK","READBACK_STATUS"), outcome=rv("PIPELINE_OUTCOME","OUTCOME_STATUS"),\n            cpuLittleMin=rv("CPU_LITTLE_MIN","STRATEGY_CPU_LITTLE_MIN"), cpuLittleMax=rv("CPU_LITTLE_MAX","STRATEGY_CPU_LITTLE_MAX"), cpuBigMin=rv("CPU_BIG_MIN","STRATEGY_CPU_BIG_MIN"), cpuBigMax=rv("CPU_BIG_MAX","STRATEGY_CPU_BIG_MAX"), gpuMin=rv("GPU_MIN","STRATEGY_GPU_MIN"), gpuMax=rv("GPU_MAX","STRATEGY_GPU_MAX"), cpuGovernor=rv("CPU_GOVERNOR","STRATEGY_CPU_GOVERNOR"), gpuGovernor=rv("GPU_GOVERNOR","STRATEGY_GPU_GOVERNOR"), powerBias=rv("POWER_BIAS","STRATEGY_POWER_BIAS"), burstLease=rv("BURST_LEASE","STRATEGY_BURST_LEASE"), comfortCeiling=rv("COMFORT_CEILING","STRATEGY_COMFORT_CEILING"), confidence=rv("STRATEGY_CONFIDENCE","CONFIDENCE"), rationale=rv("STRATEGY_RATIONALE","RATIONALE"), fpsOutcome=rv("OUTCOME_FPS","FPS_OUTCOME"), frameOutcome=rv("OUTCOME_FRAME_MS","FRAME_OUTCOME"), thermalOutcome=rv("OUTCOME_THERMAL","THERMAL_OUTCOME"), powerOutcome=rv("OUTCOME_POWER","POWER_OUTCOME"), learningSamples=rv("LEARNING_SAMPLES"), learningConfidence=rv("LEARNING_CONFIDENCE"), learningPromotion=rv("LEARNING_PROMOTION","LEARNING_STATUS")\n        )\n\n'''
rs=rs.replace(needle,truth+needle,1)
# Add named argument.
needle2='            bugHealth=mapped.bugHealth\n'
if needle2 not in rs: raise SystemExit('R13_FAIL=bughealth-arg')
rs=rs.replace(needle2,'            bugHealth=mapped.bugHealth,\n            strategy=strategy\n',1)
r.write_text(rs)

ms=m.read_text(); ms=ms.replace('CONTROL CENTER • v0.12.1-r12 • USER DESIGN • REALTIME 1s','CONTROL CENTER • v0.12.1-r13 • COMPLETE USER DESIGN • REALTIME 1s')
# Replace r12 cards with bound runtime truth.
start=ms.index('@Composable fun StrategyCompositionCard(s:RuntimeState)')
end=ms.index('@Composable fun ThermalRow(s:RuntimeState)',start)
cards='''@Composable fun StrategyCompositionCard(s:RuntimeState){ val x=s.strategy\n    BoxCard("STRATEGY COMPOSITION","Source: ${x.source}\\nMode: ${s.userMode}\\nCPU LITTLE: ${x.cpuLittleMin} → ${x.cpuLittleMax}\\nCPU BIG: ${x.cpuBigMin} → ${x.cpuBigMax}\\nGPU: ${x.gpuMin} → ${x.gpuMax}\\nCPU governor: ${x.cpuGovernor} • GPU governor: ${x.gpuGovernor}\\nPower/bias: ${x.powerBias} • Burst/lease: ${x.burstLease}\\nComfort ceiling: ${x.comfortCeiling} • Confidence: ${x.confidence}\\nRationale: ${x.rationale}",true)\n}\n@Composable fun DecisionPipelineCard(s:RuntimeState){ val x=s.strategy\n    BoxCard("DECISION PIPELINE","PROPOSED: ${x.proposal}\\nVALIDATED / REJECTED: ${x.validation}\\nAPPLIED: ${x.applied}\\nREADBACK VERIFIED: ${x.readback}\\nOUTCOME: ${x.outcome}\\nDecision source: ${x.source}",true)\n}\n@Composable fun OutcomeLearningCard(s:RuntimeState){ val x=s.strategy\n    BoxCard("OUTCOME + LEARNING","FPS: ${x.fpsOutcome} • Frame: ${x.frameOutcome}\\nThermal: ${x.thermalOutcome} • Power: ${x.powerOutcome}\\nLearning samples: ${x.learningSamples}\\nLearning confidence: ${x.learningConfidence}\\nPromotion: ${x.learningPromotion}\\nOnly module-published truth is displayed; missing fields remain unavailable.",true)\n}\n\n'''
ms=ms[:start]+cards+ms[end:]
# Turn existing vault UI into explicit four-slot manual selector. Existing bridge remains authoritative and masked.
ms=ms.replace('BoxCard("GEMINI KEY VAULT • r9",vaultStatus,true)','BoxCard("GEMINI KEY VAULT • 4 MANUAL SLOTS",vaultStatus+"\\nSlots: KEY 1 • KEY 2 • KEY 3 • KEY 4\\nSelection is manual. HTTP 429 never rotates keys automatically.",true)')
ms=ms.replace('label={Text("Vault index")}', 'label={Text("Active slot 1–4")}',1)
# constrain slot selection to 1..4 in UI action enablement and input.
ms=ms.replace('onValueChange={vaultIndex=it.filter(Char::isDigit)}','onValueChange={vaultIndex=it.filter(Char::isDigit).take(1)}',1)
ms=ms.replace('enabled=bridgeOp==null&&vaultIndex.isNotBlank()', 'enabled=bridgeOp==null&&vaultIndex in listOf("1","2","3","4")')
# Add explicit slot buttons before status box.
slot_anchor='BoxCard("GEMINI KEY VAULT • 4 MANUAL SLOTS",vaultStatus+"\\nSlots: KEY 1 • KEY 2 • KEY 3 • KEY 4\\nSelection is manual. HTTP 429 never rotates keys automatically.",true)'
slot_ui=slot_anchor+'\n        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("1","2","3","4").forEach{n->OutlinedButton(onClick={vaultIndex=n},modifier=Modifier.weight(1f)){Text("KEY $n")}}}'
ms=ms.replace(slot_anchor,slot_ui,1)
m.write_text(ms)
print('R13_BASELINE=R11_ADDITIVE')
print('R13_STRATEGY_TRUTH=MODULE_PUBLISHED_ONLY')
print('R13_PIPELINE=BOUND')
print('R13_OUTCOME_LEARNING=BOUND')
print('R13_KEY_VAULT=FOUR_MANUAL_SLOTS')
print('R13_429_AUTOROTATE=DISABLED_BY_DESIGN')
