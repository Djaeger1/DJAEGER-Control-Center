#!/usr/bin/env python3
from pathlib import Path

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt')
s=p.read_text()
start=s.index('        val strategy=StrategyTruth(')
end=s.index('\n\n        RuntimeState(',start)
new='''        // FIX2: bind the module-published STRATEGY_RESULT into the UI pipeline.
        // The mapper already carried this section, but the previous repository
        // discarded it and hard-coded APPLIED/READBACK as UNAVAILABLE.
        val sr=AtomicSnapshot.keyValues(mapped.strategyResult)
        fun srVal(key:String):String=sr[key]?.trim().orEmpty()
        val srSource=srVal("EXEC_SOURCE").ifBlank{rv("DECISION_SOURCE","decision_source","SOURCE")}
        val srValidation=srVal("VALIDATION").ifBlank{plan?.let{"${it.state} score=${it.score}: ${it.reason}"}?:"UNAVAILABLE"}
        val srApplied=when{
            srVal("PIPELINE_APPLIED").equals("YES",true)&&srVal("APPLIED_PROFILE").isNotBlank()->"YES • profile=${srVal("APPLIED_PROFILE")}"
            srVal("PIPELINE_APPLIED").isNotBlank()->srVal("PIPELINE_APPLIED")
            srVal("APPLIED_PROFILE").isNotBlank()->srVal("APPLIED_PROFILE")
            else->"UNAVAILABLE"
        }
        val srReadback=srVal("READBACK").ifBlank{srVal("PIPELINE_READBACK_VERIFIED").ifBlank{"UNAVAILABLE"}}
        val srOutcome=srVal("OUTCOME").ifBlank{dec?.outcome?:"UNAVAILABLE"}
        val strategy=StrategyTruth(
            source=srSource,
            proposal=if(srVal("PIPELINE_PROPOSED").equals("YES",true)) plan?.let{"LAST PROMOTED @${it.epoch}: ${it.mode} ${it.profile}"}?:"YES" else plan?.let{"LAST PROMOTED @${it.epoch}: ${it.mode} ${it.profile}"}?:"UNAVAILABLE",
            validation=srValidation,
            applied=srApplied,
            readback=srReadback,
            outcome=srOutcome,
            cpuLittleMin=plan?.lmin?:"—",cpuLittleMax=plan?.lmax?:"—",cpuBigMin=plan?.bmin?:"—",cpuBigMax=plan?.bmax?:"—",gpuMin=plan?.gmin?:"—",gpuMax=plan?.gmax?:"—",
            confidence=plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE"),
            rationale=plan?.reason?:rv("STRATEGY_RATIONALE","RATIONALE"),
            fpsOutcome=if(frameFresh) frameLine.getOrNull(3)?:"—" else dec?.actualFps?:"—",
            frameOutcome=if(frameFresh) frameLine.getOrNull(2)?:"—" else "—",
            thermalOutcome=dec?.actualSkin?:"—",
            powerOutcome=if(tel.powerValid=="VALID") "${tel.powerMw} mW" else "—",
            learningSamples=srVal("LEARNED_SAMPLES").ifBlank{rv("LEARNING_SAMPLES","SAMPLES")},
            learningConfidence=rv("LEARNING_CONFIDENCE","CONFIDENCE"),
            learningPromotion=srVal("LEARNING_PROMOTION").ifBlank{rv("LEARNED_STATE","LEARNING_STATUS")}
        )'''
s=s[:start]+new+s[end:]
p.write_text(s)
S=p.read_text()
assert 'val sr=AtomicSnapshot.keyValues(mapped.strategyResult)' in S
assert 'val srApplied=when{' in S
assert 'val srReadback=srVal("READBACK")' in S
assert 'applied="UNAVAILABLE — requires fresh __EXECUTION__"' not in S
assert 'readback="UNAVAILABLE — no verified readback evidence"' not in S
print('R39_STRATEGY_RESULT_BOUND=PASS')
print('R39_APPLIED_READBACK_FROM_MODULE=PASS')
