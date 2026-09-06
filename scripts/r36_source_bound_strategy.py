#!/usr/bin/env python3
# R36 source-bound strategy truth; second commit intentionally triggers the newly added workflow.
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12360',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r36"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r34 • CLOUDFLARE TRUTH MAPPING','CONTROL CENTER • v0.12.1-r36 • SOURCE-BOUND STRATEGY TRUTH',1).replace('v0.12.1-r34','v0.12.1-r36')

old='''    val policyLine=s.log.lineSequence().filter{it.contains("PREDICTOR POLICY ACTION=")}.lastOrNull().orEmpty()
    val commitLine=s.log.lineSequence().filter{it.contains("CLOUD_STRATEGY_COMMITTED")}.lastOrNull().orEmpty()
    val hierarchyLine=s.log.lineSequence().filter{it.contains("HIERARCHY ") && it.contains(" ACTION=")}.lastOrNull().orEmpty()
'''
new='''    // R36: never mix historical cloud-policy events into Local AI strategy truth.
    // Historical policy is also non-current whenever the runtime session is inactive.
    val latestPolicyLine=s.log.lineSequence().filter{it.contains("PREDICTOR POLICY ACTION=")}.lastOrNull().orEmpty()
    val latestCommitLine=s.log.lineSequence().filter{it.contains("CLOUD_STRATEGY_COMMITTED")}.lastOrNull().orEmpty()
    val latestHierarchyLine=s.log.lineSequence().filter{it.contains("HIERARCHY ") && it.contains(" ACTION=")}.lastOrNull().orEmpty()
    val cloudStrategyEventsCurrent=s.active=="1" && strategySource!="LOCAL AI"
    val policyLine=if(cloudStrategyEventsCurrent) latestPolicyLine else ""
    val commitLine=if(cloudStrategyEventsCurrent) latestCommitLine else ""
    val hierarchyLine=if(cloudStrategyEventsCurrent) latestHierarchyLine else ""
'''
assert old in ms, 'R36 policy event anchor missing'
ms=ms.replace(old,new,1)

old2='''    val cloudNarrativeFresh=thoughtSource in setOf("GEMINI","GROQ","CLOUDFLARE") && !cloudStale && publishedThoughtText.isNotBlank()
    val localNarrativeFresh=thoughtSource=="LOCAL AI" && publishedThoughtText.isNotBlank()
'''
new2='''    val cloudNarrativeFresh=s.active=="1" && thoughtSource in setOf("GEMINI","GROQ","CLOUDFLARE") && !cloudStale && publishedThoughtText.isNotBlank()
    val localNarrativeFresh=s.active=="1" && thoughtSource=="LOCAL AI" && publishedThoughtText.isNotBlank()
'''
assert old2 in ms, 'R36 narrative freshness anchor missing'
ms=ms.replace(old2,new2,1)

old3='''    val humanStrategy=when{
        cloudNarrativeFresh->"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"
        localNarrativeFresh->"PEMIKIRAN LOCAL AI\\n$publishedThoughtText"
        else->"BAHASA MANUSIA\\n$fallbackHuman"
    }'''
new3='''    val humanStrategy=when{
        cloudNarrativeFresh && strategySource=="LOCAL AI"->"PEMIKIRAN $thoughtSource (ADVISORY / TIDAK DIEKSEKUSI)\\n$publishedThoughtText"
        cloudNarrativeFresh->"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"
        localNarrativeFresh->"PEMIKIRAN LOCAL AI\\n$publishedThoughtText"
        else->"BAHASA MANUSIA\\n$fallbackHuman"
    }'''
assert old3 in ms, 'R36 humanStrategy anchor missing'
ms=ms.replace(old3,new3,1)

old4='''    val technicalStrategy="STRATEGI\\n"+
        "Keputusan: $strategyAction\\n"+'''
new4='''    val decisionView=if(strategySource=="LOCAL AI" && strategyAction=="—") "LOCAL AI / policy cloud tidak diterapkan" else strategyAction
    val technicalStrategy="STRATEGI\\n"+
        "Keputusan: $decisionView\\n"+'''
assert old4 in ms, 'R36 technical strategy anchor missing'
ms=ms.replace(old4,new4,1)

for required in [
    'val cloudStrategyEventsCurrent=s.active=="1" && strategySource!="LOCAL AI"',
    'val policyLine=if(cloudStrategyEventsCurrent) latestPolicyLine else ""',
    'PEMIKIRAN $thoughtSource (ADVISORY / TIDAK DIEKSEKUSI)',
    'LOCAL AI / policy cloud tidak diterapkan',
    'CONTROL CENTER • v0.12.1-r36 • SOURCE-BOUND STRATEGY TRUTH',
]: assert required in ms, required
for required in ['val cfEnvelopeCurrent=','thoughtField(s.envelope,"local_validation")','thoughtField(s.envelope,"resource_disposition")','Text("SLOT 1")','Text("SLOT 2")','Text("SLOT 3")']:
    assert required in ms, 'preserved contract missing: '+required
m.write_text(ms)
print('R36_POLICY_EVENTS=SOURCE_BOUND')
print('R36_INACTIVE_SESSION=NO_HISTORICAL_POLICY_AS_CURRENT')
print('R36_CLOUD_REASONING_WHILE_LOCAL_STRATEGY=ADVISORY')
print('R36_R34_ENVELOPE_TRUTH=PRESERVED')
print('R36_EXTRA_ROOT_READS=0')
