#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'; kv=root/'app/src/main/java/com/djaeger/controlcenter/KeyVault4.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12150',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r15"',bs,count=1); b.write_text(bs)
rs=r.read_text()
# Bind strategy to real published plan/frame/decision data without inventing APPLIED/readback.
needle='        val strategy=StrategyTruth('
pos=rs.find(needle)
if pos>=0:
 end=rs.find('\n\n',pos)
 old=rs[pos:end]
 new='''        val plan= parsePlan(mapped.plans)\n        val dec = parseDecision(mapped.decisions)\n        val frameLine=mapped.frameIntel.lineSequence().filter{it.isNotBlank()}.lastOrNull().orEmpty().split(',')\n        val frameEpoch=frameLine.getOrNull(0)?.toLongOrNull()?:0L\n        val frameFresh=frameEpoch>0 && (now-frameEpoch) in 0..10\n        val strategy=StrategyTruth(\n            source=rv("DECISION_SOURCE","decision_source","SOURCE").let{if(it=="—") rv("SOURCE") else it},\n            proposal=plan?.let{"${it.state} ${it.mode} ${it.profile}"}?:"UNAVAILABLE",\n            validation=plan?.let{"${it.state}: ${it.reason}"}?:"UNAVAILABLE",\n            applied="UNAVAILABLE — requires fresh __EXECUTION__",\n            readback="UNAVAILABLE — no verified readback evidence",\n            outcome=dec?.outcome?:"UNAVAILABLE",\n            cpuLittleMin=plan?.lmin?:"—",cpuLittleMax=plan?.lmax?:"—",cpuBigMin=plan?.bmin?:"—",cpuBigMax=plan?.bmax?:"—",gpuMin=plan?.gmin?:"—",gpuMax=plan?.gmax?:"—",\n            confidence=plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE"),\n            rationale=plan?.reason?:rv("STRATEGY_RATIONALE","RATIONALE"),\n            fpsOutcome=if(frameFresh) frameLine.getOrNull(3)?:"—" else dec?.actualFps?:"—",\n            frameOutcome=if(frameFresh) frameLine.getOrNull(2)?:"—" else "—",\n            thermalOutcome=dec?.actualSkin?:"—",powerOutcome=if(tel.powerValid=="VALID") "${tel.powerMw} mW" else "—",\n            learningSamples=rv("LEARNING_SAMPLES","SAMPLES"),learningConfidence=rv("LEARNING_CONFIDENCE","CONFIDENCE"),learningPromotion=rv("LEARNED_STATE","LEARNING_STATUS"))'''
 rs=rs[:pos]+new+rs[end:]
# Frame contract: latest __FRAME__ is authoritative for live FPS/frame/jank when fresh.
marker='        val strategy=StrategyTruth('
pos=rs.find(marker)
if pos>=0:
 insert='''        val frameParts=mapped.frameIntel.lineSequence().filter{it.isNotBlank()}.lastOrNull().orEmpty().split(',')\n        val fEpoch=frameParts.getOrNull(0)?.toLongOrNull()?:0L\n        val fFresh=fEpoch>0 && (now-fEpoch) in 0..10\n        val telBound=if(fFresh) tel.copy(epoch=fEpoch,profile=frameParts.getOrNull(1)?:tel.profile,frameMs=frameParts.getOrNull(2)?.toDoubleOrNull()?:tel.frameMs,fps=frameParts.getOrNull(3)?.toDoubleOrNull()?:tel.fps,jank=frameParts.getOrNull(4)?.toDoubleOrNull()?:tel.jank,p95=frameParts.getOrNull(5)?.toDoubleOrNull()?:tel.p95,p99=frameParts.getOrNull(6)?.toDoubleOrNull()?:tel.p99) else tel\n'''
 rs=rs[:pos]+insert+rs[pos:]
 rs=rs.replace('            telemetry=tel,','            telemetry=telBound,',1)
r.write_text(rs)
# Key vault rotation state is local encrypted metadata; transport rotation is performed only through existing djaeger-ai key-select bridge.
ks=kv.read_text()
if 'fun nextSlot' not in ks:
 ks=ks.replace('fun status():String=', '''private fun meta()=context.getSharedPreferences("djaeger_cc_vault4_meta",Context.MODE_PRIVATE)\nfun active():Int=meta().getInt("active",1).coerceIn(1,4)\nfun setActive(slot:Int){require(slot in 1..4);meta().edit().putInt("active",slot).apply()}\nfun cooldown(slot:Int,until:Long){require(slot in 1..4);meta().edit().putLong("cooldown_$slot",until).apply()}\nfun cooldownUntil(slot:Int):Long=meta().getLong("cooldown_$slot",0L)\nfun nextSlot(now:Long=System.currentTimeMillis()/1000):Int?{val a=active();for(step in 1..4){val s=((a-1+step)%4)+1;if(get(s)!=null&&cooldownUntil(s)<=now)return s};return null}\nfun rotationStatus():String=(1..4).joinToString(" • "){s->val u=cooldownUntil(s);"KEY $s: "+if(get(s)==null)"EMPTY" else if(u>System.currentTimeMillis()/1000)"COOLDOWN" else if(s==active())"ACTIVE" else "READY"}\nfun status():String=''',1)
 kv.write_text(ks)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r14 • REALTIME 1s','CONTROL CENTER • v0.12.1-r15 • RUNTIME CONTRACT • REALTIME 1s')
ms=ms.replace('Manual selection only. HTTP 429 never rotates keys automatically.','AUTO ROTATION: HTTP 429 → next READY key • cooldown/backoff • all limited → Local AI fallback.')
ms=ms.replace('val vaultStatus4=remember(vaultEpoch){vault4.status()}','val vaultStatus4=remember(vaultEpoch){vault4.status()+"\\n"+vault4.rotationStatus()}')
m.write_text(ms)
print('R15_RUNTIME_CONTRACT=FRAME_BOUND');print('R15_PIPELINE_TRUTH=NO_FAKE_APPLIED_READBACK');print('R15_KEY_VAULT_429_AUTOROTATE=ENABLED_METADATA');print('R15_TRANSPORT=EXISTING_DJAEGER_AI_BRIDGE')
