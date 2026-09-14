from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); c=mapper.read_text(); b=build.read_text()

# Exact additive derivative of vc12257 / module vc129630.
assert 'versionCode = 12257' in b
assert 'versionName = "0.12.1-rebuild3-lang3-mwfix2-attr1-math1-sync4"' in b
b=b.replace('versionCode = 12257','versionCode = 12258',1)
b=b.replace('versionName = "0.12.1-rebuild3-lang3-mwfix2-attr1-math1-sync4"','versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1"',1)

# Snapshot mapper: consume three new read-only sections. No extra root/sysfs polling.
old='''        val hermesMath: String,\n        val controlCenterSync: String,'''
new='''        val hermesMath: String,\n        val hermesKernel1: String,\n        val agentSysfs1Capability: String,\n        val agentSysfs1Execution: String,\n        val controlCenterSync: String,'''
assert old in c
c=c.replace(old,new,1)
old='''            hermesMath = s["HERMES_MATH"].orEmpty(),\n            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),'''
new='''            hermesMath = s["HERMES_MATH"].orEmpty(),\n            hermesKernel1 = s["HERMES_KERNEL1"].orEmpty(),\n            agentSysfs1Capability = s["AGENT_SYSFS1_CAPABILITY"].orEmpty(),\n            agentSysfs1Execution = s["AGENT_SYSFS1_EXECUTION"].orEmpty(),\n            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),'''
assert old in c
c=c.replace(old,new,1)

# Runtime state carries the already-atomic module publication only.
old='''val hermesLanguage:String="",val hermesMath:String="",val controlCenterSync:String="",'''
new='''val hermesLanguage:String="",val hermesMath:String="",val hermesKernel1:String="",val agentSysfs1Capability:String="",val agentSysfs1Execution:String="",val controlCenterSync:String="",'''
assert old in r
r=r.replace(old,new,1)
old='''hermesLanguage=mapped.hermesLanguage,hermesMath=mapped.hermesMath,controlCenterSync=mapped.controlCenterSync,'''
new='''hermesLanguage=mapped.hermesLanguage,hermesMath=mapped.hermesMath,hermesKernel1=mapped.hermesKernel1,agentSysfs1Capability=mapped.agentSysfs1Capability,agentSysfs1Execution=mapped.agentSysfs1Execution,controlCenterSync=mapped.controlCenterSync,'''
assert old in r
r=r.replace(old,new,1)

# Header identity: preserve all existing UI, append the two new capabilities.
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1' in m
m=m.replace('CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1','CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1',1)

# Exact matched contract: no mixed module/app revision accepted as MATCHED.
old='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_SYNC4"&&syncModule=="129630"&&syncCc=="12257"'
new='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1"&&syncModule=="129631"&&syncCc=="12258"'
assert old in m
m=m.replace(old,new,1)

# Compact module identity recognizes CCSYNC1 first, leaving every older mapping intact.
old='''private fun compactModuleVersion(raw:String):String=when{\n    raw.contains("ATTR1",true)&&raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1"'''
new='''private fun compactModuleVersion(raw:String):String=when{\n    raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1"\n    raw.contains("ATTR1",true)&&raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1"'''
assert old in m
m=m.replace(old,new,1)

# Make Agent/Hermes labels reflect the new body/brain capabilities without moving existing cards.
assert 'BoxCard("AI AGENT • FULL HARDWARE CONTROLLER",body,true)' in m
m=m.replace('BoxCard("AI AGENT • FULL HARDWARE CONTROLLER",body,true)','BoxCard("AI AGENT • SYSFS1 • FULL HARDWARE CONTROLLER",body,true)',1)
assert 'BoxCard("HERMES H2 • LANG3 + MATH1",body,true)' in m
m=m.replace('BoxCard("HERMES H2 • LANG3 + MATH1",body,true)','BoxCard("HERMES H2 • KERNEL1 • LANG3 + MATH1",body,true)',1)

# New compact truth card. It reads only cc_snapshot fields and adds no hardware authority to the APK.
anchor='''@Composable fun HermesCard(s:RuntimeState){'''
assert anchor in m
card='''@Composable fun KernelAgentSyncCard(s:RuntimeState){\n    val kState=envField(s.hermesKernel1,"STATE").ifBlank{"UNAVAILABLE"}\n    val kStrategy=envField(s.hermesKernel1,"STRATEGY").ifBlank{"—"}\n    val kBottleneck=envField(s.hermesKernel1,"BOTTLENECK").ifBlank{"—"}\n    val kCaps=envField(s.hermesKernel1,"CAPABILITIES_TOTAL").ifBlank{envField(s.agentSysfs1Capability,"TOTAL").ifBlank{"0"}}\n    val kActs=envField(s.hermesKernel1,"ACTUATORS_TOTAL").ifBlank{envField(s.agentSysfs1Capability,"ACTUATORS").ifBlank{"0"}}\n    val kActions=envField(s.hermesKernel1,"ACTION_COUNT").ifBlank{"0"}\n    val kMem=envField(s.hermesKernel1,"MEMORY_SAMPLES").ifBlank{"0"}\n    val kOk=envField(s.hermesKernel1,"MEMORY_SUCCESS").ifBlank{"0"}\n    val kBad=envField(s.hermesKernel1,"MEMORY_FAILED").ifBlank{"0"}\n    val execStatus=envField(s.agentSysfs1Execution,"STATUS").ifBlank{"IDLE / NO EXECUTION YET"}\n    val execStrategy=envField(s.agentSysfs1Execution,"STRATEGY_ID").ifBlank{"—"}\n    val execCount=envField(s.agentSysfs1Execution,"ACTION_COUNT").ifBlank{"0"}\n    val execApplied=envField(s.agentSysfs1Execution,"APPLIED_COUNT").ifBlank{"0"}\n    val execFail=envField(s.agentSysfs1Execution,"FAILURE").ifBlank{"NONE"}\n    val rootOwner=envField(s.hermesKernel1,"ROOT_AUTHORITY_OWNER").ifBlank{"AI_AGENT"}\n    val sysfsOwner=envField(s.hermesKernel1,"SYSFS_OWNER").ifBlank{"AI_AGENT"}\n    val body="Hermes kernel model: $kState\\nStrategy: $kStrategy\\nBottleneck: $kBottleneck\\nKernel capabilities: $kCaps • writable actuators: $kActs\\nPlanned actions: $kActions\\nHistorical kernel outcomes: $kMem • success $kOk • failed $kBad\\n\\nAgent SYSFS1 execution: $execStatus\\nStrategy ID: $execStrategy\\nActions: $execApplied / $execCount applied\\nFailure: $execFail\\nRoot Authority owner: $rootOwner\\nSysfs owner: $sysfsOwner\\nExecution owner: AI_AGENT\\nHermes direct hardware writes: 0"\n    BoxCard("HERMES KERNEL1 ↔ AI AGENT SYSFS1",body,true)\n}\n\n'''
m=m.replace(anchor,card+anchor,1)

# Preserve the Overview order and every existing card; add only one card between Agent and Hermes.
old='''AgentRebuild3Card(s);HermesCard(s);HumanComfortHcc1Card(s)'''
new='''AgentRebuild3Card(s);KernelAgentSyncCard(s);HermesCard(s);HumanComfortHcc1Card(s)'''
assert old in m
m=m.replace(old,new,1)

main.write_text(m); repo.write_text(r); mapper.write_text(c); build.write_text(b)

# Build-time invariants.
M=main.read_text(); R=repo.read_text(); C=mapper.read_text(); B=build.read_text()
assert 'versionCode = 12258' in B and '0.12.1-rebuild3-hk1-sysfs1-ccsync1' in B
assert 'REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1' in M
assert 'syncModule=="129631"&&syncCc=="12258"' in M
assert 'HERMES_KERNEL1' in C and 'AGENT_SYSFS1_CAPABILITY' in C and 'AGENT_SYSFS1_EXECUTION' in C
assert 'hermesKernel1=mapped.hermesKernel1' in R and 'agentSysfs1Execution=mapped.agentSysfs1Execution' in R
assert 'KernelAgentSyncCard(s);HermesCard(s)' in M
assert 'ProcessBuilder("su"' in R  # existing manual controls preserved
assert 'AGENT_WINNER' not in M and 'LOCAL AI' not in M
print('HK1_SYSFS1_CCSYNC1_CC_PATCH=PASS')
print('MATCHED_MODULE_VC=129631')
print('CONTROL_CENTER_VC=12258')
print('EXISTING_UI_PRESERVED=YES')
print('NEW_RECURRING_ROOT_READS=0')
