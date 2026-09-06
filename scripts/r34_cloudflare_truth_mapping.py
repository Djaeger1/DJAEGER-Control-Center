#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12340',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r34"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r33 • CLOUDFLARE 3 AUTO SLOTS','CONTROL CENTER • v0.12.1-r34 • CLOUDFLARE TRUTH MAPPING',1).replace('v0.12.1-r33','v0.12.1-r34')

anchor='''    val confidence=logToken(policyLine,"CONF").takeIf{it!="—"}?:s.strategy.confidence.ifBlank{"—"}\n'''
assert anchor in ms, 'R34 confidence anchor missing'
insert='''    val confidence=logToken(policyLine,"CONF").takeIf{it!="—"}?:s.strategy.confidence.ifBlank{"—"}\n\n    fun validRange(v:String)=v.matches(Regex("^[0-9]+-[0-9]+$"))\n    fun oldRange(a:String,b:String)=if(a.matches(Regex("^[0-9]+$"))&&b.matches(Regex("^[0-9]+$"))) "$a-$b" else "—"\n    fun canonicalMode(v:String)=when(v.trim().uppercase()){\n        "SEDANG","MEDIUM","COMFORTABLE"->"NYAMAN"\n        "COOL"->"DINGIN"\n        "WARM"->"HANGAT"\n        "HOT"->"PANAS"\n        else->v.trim().uppercase()\n    }\n    val envAt=thoughtField(s.envelope,"updated_at").toLongOrNull()?:0L\n    val envFresh=envAt>0 && (nowEpoch-envAt) in 0..300\n    val envSource=thoughtField(s.envelope,"source").uppercase()\n    val envGame=thoughtField(s.envelope,"game")\n    val envWindow=thoughtField(s.envelope,"window_mode")\n    val envMode=thoughtField(s.envelope,"user_mode")\n    val cfEnvelopeCurrent=strategySource=="CLOUDFLARE" && envFresh && envSource.startsWith("CLOUDFLARE") &&\n        (envGame.isBlank()||envGame==s.game) && (envWindow.isBlank()||envWindow==s.window) &&\n        (envMode.isBlank()||canonicalMode(envMode)==canonicalMode(s.userMode))\n\n    val policyLittle=logToken(policyLine,"L")\n    val policyBig=logToken(policyLine,"B")\n    val policyGpu=logToken(policyLine,"G")\n    val envLittle=thoughtField(s.envelope,"little_khz")\n    val envBig=thoughtField(s.envelope,"big_khz")\n    val envGpu=thoughtField(s.envelope,"gpu_mhz")\n    val oldLittle=oldRange(s.strategy.cpuLittleMin,s.strategy.cpuLittleMax)\n    val oldBig=oldRange(s.strategy.cpuBigMin,s.strategy.cpuBigMax)\n    val oldGpu=oldRange(s.strategy.gpuMin,s.strategy.gpuMax)\n    fun cloudRange(env:String,policy:String,legacy:String)=when{\n        cfEnvelopeCurrent&&validRange(env)->env\n        strategySource=="CLOUDFLARE"&&validRange(policy)->policy\n        validRange(legacy)->legacy\n        else->"—"\n    }\n    val littleRange=if(strategySource=="CLOUDFLARE") cloudRange(envLittle,policyLittle,oldLittle) else oldLittle\n    val bigRange=if(strategySource=="CLOUDFLARE") cloudRange(envBig,policyBig,oldBig) else oldBig\n    val gpuRange=if(strategySource=="CLOUDFLARE") cloudRange(envGpu,policyGpu,oldGpu) else oldGpu\n    val keepSuffix=if(strategyAction.uppercase()=="KEEP") " • KEEP" else ""\n    fun rangeView(v:String,unit:String)=if(validRange(v)) "$v $unit$keepSuffix" else "— (PROFILE / tidak ada override numerik)"\n\n    val envValidation=thoughtField(s.envelope,"local_validation").uppercase()\n    val logValidation=logToken(policyLine,"LOCAL_VALIDATION").uppercase()\n    val validationTruth=when{\n        strategySource!="CLOUDFLARE"->s.strategy.validation.ifBlank{"—"}\n        cfEnvelopeCurrent && envValidation in setOf("VALIDATED","REPAIRED")->envValidation\n        logValidation in setOf("VALIDATED","REPAIRED")->logValidation\n        else->s.strategy.validation.takeIf{it.isNotBlank()&&!it.startsWith("UNAVAILABLE",true)}?:"UNAVAILABLE"\n    }\n    val operationalConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"confidence").ifBlank{confidence} else confidence\n    val rawCloudConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"model_confidence_raw") else ""\n    val confidenceView=if(rawCloudConfidence.matches(Regex("^[0-9]+$")) && rawCloudConfidence!=operationalConfidence)\n        "$operationalConfidence% (Cloudflare raw: $rawCloudConfidence%)" else "$operationalConfidence%"\n    val resourceDisposition=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"resource_disposition") else ""\n'''
ms=ms.replace(anchor,insert,1)

# Human summary and technical view must use current validated envelope truth for Cloudflare.
ms=ms.replace('''        "Rencana resource: CPU little ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz, "+\n        "CPU big ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz, dan GPU ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz. "+''','''        "Rencana resource: CPU little $littleRange kHz, CPU big $bigRange kHz, dan GPU $gpuRange MHz. "+''',1)
ms=ms.replace('''        "CPU little: ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz\\n"+\n        "CPU big: ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz\\n"+\n        "GPU: ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz\\n"+''','''        "CPU little: ${rangeView(littleRange,"kHz")}\\n"+\n        "CPU big: ${rangeView(bigRange,"kHz")}\\n"+\n        "GPU: ${rangeView(gpuRange,"MHz")}\\n"+''',1)
ms=ms.replace('''        "Confidence: $confidence%\\n"+\n        "Review ulang: $review\\n"+\n        "Validasi Local AI: ${s.strategy.validation.ifBlank{"—"}}"''','''        "Confidence: $confidenceView\\n"+\n        "Review ulang: $review\\n"+\n        "Validasi Local AI: $validationTruth"+\n        (if(resourceDisposition.isNotBlank()) "\\nResource: $resourceDisposition" else "")''',1)

assert 'CONTROL CENTER • v0.12.1-r34 • CLOUDFLARE TRUTH MAPPING' in ms
assert 'val cfEnvelopeCurrent=' in ms
assert 'thoughtField(s.envelope,"local_validation")' in ms
assert 'thoughtField(s.envelope,"model_confidence_raw")' in ms
assert 'thoughtField(s.envelope,"resource_disposition")' in ms
assert 'CPU little: ${rangeView(littleRange,"kHz")}' in ms
assert 'Validasi Local AI: $validationTruth' in ms
assert 'Cloudflare raw: $rawCloudConfidence%' in ms
# R33 slot UX and authority remain untouched.
for x in ['Text("SLOT 1")','Text("SLOT 2")','Text("SLOT 3")','sticky healthy → failover 401/403/429','fun cloudIsActive(state:String)=state=="ACTIVE"']:
    assert x in ms, x
m.write_text(ms)

print('R34_CLOUDFLARE_KEEP_RANGE=VALIDATED_ENVELOPE_TRUTH')
print('R34_LOCAL_VALIDATION=BACKEND_PUBLISHED_TRUTH')
print('R34_CONFIDENCE=OPERATIONAL_PLUS_RAW_TRANSPARENT')
print('R34_PROFILE_NO_OVERRIDE=EXPLICIT_NOT_BARE_DASH')
print('R34_EXTRA_ROOT_READS=0')
print('R34_R33_THREE_SLOT_UI=PRESERVED')
