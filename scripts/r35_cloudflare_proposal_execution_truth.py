#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12350',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r35"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r34 • CLOUDFLARE TRUTH MAPPING','CONTROL CENTER • v0.12.1-r35 • PROPOSAL / EXECUTION TRUTH',1).replace('v0.12.1-r34','v0.12.1-r35')

# R34 gated Cloudflare envelope truth on final strategySource==CLOUDFLARE. That is
# wrong for a valid Cloudflare KEEP/PROFILE proposal whose execution owner is
# intentionally LOCAL_AI. Proposal truth and execution truth are separate.
old='''    val cfEnvelopeCurrent=strategySource=="CLOUDFLARE" && envFresh && envSource.startsWith("CLOUDFLARE") &&
        (envGame.isBlank()||envGame==s.game) && (envWindow.isBlank()||envWindow==s.window) &&
        (envMode.isBlank()||canonicalMode(envMode)==canonicalMode(s.userMode))
'''
new='''    val cloudProposalCurrent=envFresh && envSource.startsWith("CLOUDFLARE") &&
        (envGame.isBlank()||envGame==s.game) && (envWindow.isBlank()||envWindow==s.window) &&
        (envMode.isBlank()||canonicalMode(envMode)==canonicalMode(s.userMode))
    val proposalSource=thoughtField(s.envelope,"proposal_source").uppercase().ifBlank{if(envSource.startsWith("CLOUDFLARE")) "CLOUDFLARE" else ""}
    val proposalValidation=thoughtField(s.envelope,"proposal_validation").uppercase()
    val executionOwner=thoughtField(s.envelope,"execution_owner").uppercase().replace("_"," ")
    val numericEnvelope=thoughtField(s.envelope,"numeric_envelope")
'''
assert old in ms, 'R35 R34 envelope gate anchor missing'
ms=ms.replace(old,new,1)

ms=ms.replace('''        cfEnvelopeCurrent&&validRange(env)->env
        strategySource=="CLOUDFLARE"&&validRange(policy)->policy
''','''        cloudProposalCurrent&&numericEnvelope=="1"&&validRange(env)->env
        strategySource=="CLOUDFLARE"&&validRange(policy)->policy
''',1)

oldv='''    val validationTruth=when{
        strategySource!="CLOUDFLARE"->s.strategy.validation.ifBlank{"—"}
        cfEnvelopeCurrent && envValidation in setOf("VALIDATED","REPAIRED")->envValidation
        logValidation in setOf("VALIDATED","REPAIRED")->logValidation
        else->s.strategy.validation.takeIf{it.isNotBlank()&&!it.startsWith("UNAVAILABLE",true)}?:"UNAVAILABLE"
    }
    val operationalConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"confidence").ifBlank{confidence} else confidence
    val rawCloudConfidence=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"model_confidence_raw") else ""
'''
newv='''    val validationTruth=when{
        cloudProposalCurrent && proposalValidation in setOf("VALIDATED","REPAIRED")->proposalValidation
        cloudProposalCurrent && envValidation in setOf("VALIDATED","REPAIRED")->envValidation
        thoughtSource=="CLOUDFLARE" && logValidation in setOf("VALIDATED","REPAIRED")->logValidation
        strategySource!="CLOUDFLARE"->s.strategy.validation.takeIf{it.isNotBlank()&&!it.startsWith("UNAVAILABLE",true)}?:"UNAVAILABLE"
        else->s.strategy.validation.takeIf{it.isNotBlank()&&!it.startsWith("UNAVAILABLE",true)}?:"UNAVAILABLE"
    }
    val operationalConfidence=if(cloudProposalCurrent) thoughtField(s.envelope,"confidence").ifBlank{confidence} else confidence
    val rawCloudConfidence=if(cloudProposalCurrent) thoughtField(s.envelope,"model_confidence_raw") else ""
'''
assert oldv in ms, 'R35 R34 validation anchor missing'
ms=ms.replace(oldv,newv,1)

ms=ms.replace('''    val resourceDisposition=if(strategySource=="CLOUDFLARE"&&cfEnvelopeCurrent) thoughtField(s.envelope,"resource_disposition") else ""
''','''    val resourceDisposition=if(cloudProposalCurrent) thoughtField(s.envelope,"resource_disposition") else ""
    val executionTruth=when{
        cloudProposalCurrent && executionOwner.isNotBlank()->executionOwner
        else->strategySource
    }
''',1)

# Label the validation correctly. It validates the cloud proposal; it does not
# imply Local AI ceased to own final execution.
ms=ms.replace('''        "Validasi Local AI: $validationTruth"+
        (if(resourceDisposition.isNotBlank()) "\\nResource: $resourceDisposition" else "")''','''        "Validasi proposal: $validationTruth"+
        (if(proposalSource.isNotBlank()) "\\nProposal: $proposalSource" else "")+
        "\\nStrategi aktif: $strategySource"+
        "\\nPemilik eksekusi: $executionTruth"+
        (if(resourceDisposition.isNotBlank()) "\\nResource: $resourceDisposition" else "")''',1)

# A non-numeric Cloudflare KEEP/PROFILE must be described as no cloud override,
# not as missing hardware knowledge.
ms=ms.replace('''    fun rangeView(v:String,unit:String)=if(validRange(v)) "$v $unit$keepSuffix" else "— (PROFILE / tidak ada override numerik)"
''','''    fun rangeView(v:String,unit:String)=if(validRange(v)) "$v $unit$keepSuffix" else if(cloudProposalCurrent&&numericEnvelope=="0") "— (KEEP PROFILE / Local AI tetap aktif)" else "— (PROFILE / tidak ada override numerik)"
''',1)

assert 'CONTROL CENTER • v0.12.1-r35 • PROPOSAL / EXECUTION TRUTH' in ms
assert 'val cloudProposalCurrent=' in ms
assert 'proposal_validation' in ms
assert 'execution_owner' in ms
assert 'numeric_envelope' in ms
assert 'Validasi proposal: $validationTruth' in ms
assert 'Strategi aktif: $strategySource' in ms
assert 'Pemilik eksekusi: $executionTruth' in ms
assert 'KEEP PROFILE / Local AI tetap aktif' in ms
m.write_text(ms)

print('R35_PROPOSAL_TRUTH=INDEPENDENT_OF_FINAL_STRATEGY_SOURCE')
print('R35_EXECUTION_OWNER=VISIBLE')
print('R35_KEEP_PROFILE=LOCAL_AI_ACTIVE_EXPLICIT')
print('R35_VALIDATION_LABEL=PROPOSAL_NOT_LOCAL_AI_AVAILABILITY')
