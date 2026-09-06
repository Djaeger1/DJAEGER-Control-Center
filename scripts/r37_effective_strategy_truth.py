#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12370',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r37"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r36 • SOURCE-BOUND STRATEGY TRUTH','CONTROL CENTER • v0.12.1-r37 • EFFECTIVE STRATEGY TRUTH',1).replace('v0.12.1-r36','v0.12.1-r37')

# The envelope belongs to the current Cloudflare proposal independently from who
# finally executes. R34 incorrectly tied envelope freshness to strategySource.
old='''    val cfEnvelopeCurrent=strategySource=="CLOUDFLARE" && envFresh && envSource.startsWith("CLOUDFLARE") &&
        (envGame.isBlank()||envGame==s.game) && (envWindow.isBlank()||envWindow==s.window) &&
        (envMode.isBlank()||canonicalMode(envMode)==canonicalMode(s.userMode))
'''
new='''    val proposalEnvelopeCurrent=envFresh && envSource.startsWith("CLOUDFLARE") &&
        (envGame.isBlank()||envGame==s.game) && (envWindow.isBlank()||envWindow==s.window) &&
        (envMode.isBlank()||canonicalMode(envMode)==canonicalMode(s.userMode))
    val cfEnvelopeCurrent=strategySource=="CLOUDFLARE" && proposalEnvelopeCurrent
'''
assert old in ms, 'R37 R34 envelope current anchor missing'
ms=ms.replace(old,new,1)

# R37 consumes the explicit FIX5 proposal/execution truth contract. Missing fields
# on an older backend fail closed to the previous R36 behavior.
old2='''    val resourceDisposition=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"resource_disposition") else ""
'''
new2='''    val resourceDisposition=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"resource_disposition") else ""
    val proposalSource=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"proposal_source").uppercase() else ""
    val proposalValidation=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"proposal_validation").uppercase() else ""
    val executionEligible=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"execution_eligible") else ""
    val executionOwner=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"execution_owner").uppercase().replace("_"," ") else ""
    val effectiveBackendSource=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"effective_strategy_source").uppercase().replace("_"," ") else ""
    val forecastValidity=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"forecast_validity").uppercase() else ""
    val numericEnvelope=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"numeric_envelope") else ""
    val cloudAdvisory=proposalEnvelopeCurrent && proposalSource=="CLOUDFLARE" && executionEligible=="0"
    val effectiveStrategyView=when{
        cloudAdvisory->"LOCAL AI"
        effectiveBackendSource.isNotBlank()->effectiveBackendSource
        else->strategySource
    }
    val executionOwnerView=when{
        cloudAdvisory->"LOCAL AI"
        executionOwner.isNotBlank()->executionOwner
        else->effectiveStrategyView
    }
    val effectiveLocal=effectiveStrategyView.startsWith("LOCAL") || effectiveStrategyView in setOf("USER MODE OFFLINE","VALIDATOR FALLBACK")
'''
assert old2 in ms, 'R37 resource disposition anchor missing'
ms=ms.replace(old2,new2,1)

# Proposal confidence remains visible even when it is not the execution owner.
ms=ms.replace('''    val operationalConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"confidence").ifBlank{confidence} else confidence
    val rawCloudConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"model_confidence_raw") else ""
''','''    val operationalConfidence=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"confidence").ifBlank{confidence} else confidence
    val rawCloudConfidence=if(proposalEnvelopeCurrent) thoughtField(s.envelope,"model_confidence_raw") else ""
''',1)

# Keep R36's early event gate unchanged. It is declared before envelope truth is
# available, so referencing cloudAdvisory/effectiveLocal here would be a forward
# reference in Kotlin. The final rendered truth below is bound to FIX5 explicit
# execution fields and therefore cannot present a repaired proposal as execution.
assert 'val cloudStrategyEventsCurrent=s.active=="1" && strategySource!="LOCAL AI"' in ms

old4='''        cloudNarrativeFresh && strategySource=="LOCAL AI"->"PEMIKIRAN $thoughtSource (ADVISORY / TIDAK DIEKSEKUSI)\\n$publishedThoughtText"
'''
new4='''        cloudNarrativeFresh && (cloudAdvisory||effectiveLocal)->"PEMIKIRAN $thoughtSource (ADVISORY / TIDAK DIEKSEKUSI)\\n$publishedThoughtText"
'''
assert old4 in ms, 'R37 R36 advisory narrative anchor missing'
ms=ms.replace(old4,new4,1)

old5='''    val decisionView=if(strategySource=="LOCAL AI" && strategyAction=="—") "LOCAL AI / policy cloud tidak diterapkan" else strategyAction
'''
new5='''    val finalLocalProfile=thoughtField(s.brain,"FINAL_PROFILE").ifBlank{"LOCAL"}
    val finalLocalMode=thoughtField(s.brain,"EXEC_MODE").ifBlank{"PROFILE"}
    val decisionView=when{
        cloudAdvisory->"LOCAL AI / ${resourceDisposition.ifBlank{"PROFILE_HOLD"}}"
        effectiveLocal && strategyAction=="—"->"LOCAL AI / policy cloud tidak diterapkan"
        else->strategyAction
    }
    val profileModeView=if(cloudAdvisory) "$finalLocalProfile / $finalLocalMode" else "$strategyProfile / $strategyMode"
    val noCloudOverride="— (LOCAL AI PROFILE / tanpa override Cloudflare)"
    val littleView=if(cloudAdvisory) noCloudOverride else rangeView(littleRange,"kHz")
    val bigView=if(cloudAdvisory) noCloudOverride else rangeView(bigRange,"kHz")
    val gpuView=if(cloudAdvisory) noCloudOverride else rangeView(gpuRange,"MHz")
    val predictionView=if(cloudAdvisory) "Advisory Cloudflare • $predictionText" else predictionText
    val riskView=if(cloudAdvisory) "Advisory Cloudflare • $riskText" else riskText
    val confidenceEffectiveView=when{
        cloudAdvisory && rawCloudConfidence.matches(Regex("^[0-9]+$"))->"Cloudflare raw $rawCloudConfidence% • tidak dipakai untuk eksekusi"
        cloudAdvisory->"Tidak berlaku untuk eksekusi Local AI"
        else->confidenceView
    }
    val validationEffectiveView=when{
        proposalEnvelopeCurrent && proposalValidation.isNotBlank()->proposalValidation
        else->validationTruth
    }
    val providerLinesEffective=buildString{
        append("Active now: $activeNow\\nCloud active: $activeCloud")
        if(proposalEnvelopeCurrent&&proposalSource.isNotBlank()) append("\\nProposal: $proposalSource / ${proposalValidation.ifBlank{"UNKNOWN"}}")
        append("\\nStrategy efektif: $effectiveStrategyView")
        append("\\nPemilik eksekusi: $executionOwnerView")
    }
'''
assert old5 in ms, 'R37 R36 decision view anchor missing'
ms=ms.replace(old5,new5,1)

# Replace only the rendered technical truth; raw cloud advisory remains visible
# but cannot masquerade as the effective strategy.
ms=ms.replace('''        "Profil / mode: $strategyProfile / $strategyMode\\n"+
        "CPU little: ${rangeView(littleRange,"kHz")}\\n"+
        "CPU big: ${rangeView(bigRange,"kHz")}\\n"+
        "GPU: ${rangeView(gpuRange,"MHz")}\\n"+
        "Prediksi: $predictionText\\n"+
        "Risiko: $riskText\\n"+
        "Confidence: $confidenceView\\n"+
        "Review ulang: $review\\n"+
        "Validasi Local AI: $validationTruth"+
        (if(resourceDisposition.isNotBlank()) "\\nResource: $resourceDisposition" else "")''','''        "Profil / mode: $profileModeView\\n"+
        "CPU little: $littleView\\n"+
        "CPU big: $bigView\\n"+
        "GPU: $gpuView\\n"+
        "Prediksi: $predictionView\\n"+
        "Risiko: $riskView\\n"+
        "Confidence: $confidenceEffectiveView\\n"+
        "Review ulang: $review\\n"+
        "Validasi proposal: $validationEffectiveView"+
        (if(forecastValidity.isNotBlank()) "\\nForecast validity: $forecastValidity" else "")+
        (if(resourceDisposition.isNotBlank()) "\\nResource: $resourceDisposition" else "")+
        (if(numericEnvelope.isNotBlank()) "\\nNumeric envelope: $numericEnvelope" else "")''',1)

ms=ms.replace('''    BoxCard("THOUGHTS", providerLines+"\\n\\n"+humanStrategy+"\\n\\n"+technicalStrategy, true)''','''    BoxCard("THOUGHTS", providerLinesEffective+"\\n\\n"+humanStrategy+"\\n\\n"+technicalStrategy, true)''',1)

for required in [
    'CONTROL CENTER • v0.12.1-r37 • EFFECTIVE STRATEGY TRUTH',
    'val proposalEnvelopeCurrent=',
    'thoughtField(s.envelope,"execution_eligible")',
    'thoughtField(s.envelope,"execution_owner")',
    'thoughtField(s.envelope,"effective_strategy_source")',
    'val cloudAdvisory=',
    'Strategy efektif: $effectiveStrategyView',
    'Pemilik eksekusi: $executionOwnerView',
    'Validasi proposal: $validationEffectiveView',
    'Cloudflare raw $rawCloudConfidence% • tidak dipakai untuk eksekusi',
    'LOCAL AI PROFILE / tanpa override Cloudflare',
    'providerLinesEffective+"\\n\\n"+humanStrategy',
]: assert required in ms, required
for required in ['Text("SLOT 1")','Text("SLOT 2")','Text("SLOT 3")','sticky healthy → failover 401/403/429']:
    assert required in ms, required
m.write_text(ms)
print('R37_EFFECTIVE_STRATEGY_SOURCE=BACKEND_TRUTH')
print('R37_EXECUTION_OWNER=BACKEND_TRUTH')
print('R37_CLOUDFLARE_REPAIRED_PROFILE_HOLD=ADVISORY_ONLY')
print('R37_FPS0_REPAIRED_FORECAST=VISIBLE_AS_VALIDITY_NOT_FINAL_TRUTH')
print('R37_RAW_CONFIDENCE=PROPOSAL_ONLY_WHEN_NONEXECUTED')
print('R37_R33_THREE_SLOT_UI=PRESERVED')
