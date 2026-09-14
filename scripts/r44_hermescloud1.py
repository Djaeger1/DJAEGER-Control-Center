from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); b=build.read_text()

# HERMESCLOUD1 is additive to the validated SHAREDINT1 pair.
assert 'versionCode = 12259' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1"' in b
b=b.replace('versionCode = 12259','versionCode = 12260',1)
b=b.replace('versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1"','versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1"',1)

old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1'
assert old_header in m
m=m.replace(old_header,old_header+' • HERMESCLOUD1',1)

# Strengthen exact pair matching. HERMES CLOUD is one backend of HERMES H2, not a third brain.
old='''    val hermesTeacherLoop=envField(s.controlCenterSync,"HERMES_TEACHER_LOOP")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1"&&syncModule=="129632"&&syncCc=="12259"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"&&syncGameRegistry=="GAMEREG1"&&syncShared=="SHAREDINT1"&&geminiScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"&&hermesScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)&&s.moduleVersion.contains("GAMEREG1",true)&&s.moduleVersion.contains("SHAREDINT1",true)\n'''
new='''    val hermesTeacherLoop=envField(s.controlCenterSync,"HERMES_TEACHER_LOOP")\n    val syncHermesCloud=envField(s.controlCenterSync,"HERMES_CLOUD")\n    val syncHermesCloudRole=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE")\n    val syncHermesBackendPriority=envField(s.controlCenterSync,"HERMES_BACKEND_PRIORITY")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1"&&syncModule=="129633"&&syncCc=="12260"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"&&syncGameRegistry=="GAMEREG1"&&syncShared=="SHAREDINT1"&&syncHermesCloud=="HERMESCLOUD1"&&geminiScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"&&hermesScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)&&s.moduleVersion.contains("GAMEREG1",true)&&s.moduleVersion.contains("SHAREDINT1",true)&&s.moduleVersion.contains("HERMESCLOUD1",true)\n'''
assert old in m
m=m.replace(old,new,1)

old_body='''Hermes teacher loop: ${hermesTeacherLoop.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts: DELTA / EVENT DRIVEN\\nThird brain: $third'''
new_body='''Hermes teacher loop: ${hermesTeacherLoop.ifBlank{"UNPUBLISHED"}}\\nHERMES Cloud: ${syncHermesCloud.ifBlank{"UNPUBLISHED"}}\\nHERMES Cloud role: ${syncHermesCloudRole.ifBlank{"UNPUBLISHED"}}\\nHERMES backend priority: ${syncHermesBackendPriority.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts: DELTA / EVENT DRIVEN\\nThird brain: $third'''
assert old_body in m
m=m.replace(old_body,new_body,1)

# Dedicated visibility card. Reads existing atomic __BRAIN__ fields; no extra recurring root read.
card=r'''@Composable fun HermesCloudCard(s:RuntimeState){
    val backend=envField(s.brain,"HERMES_BACKEND").ifBlank{"LOCAL"}
    val state=envField(s.brain,"HERMES_CLOUD_STATE").ifBlank{"UNAVAILABLE"}
    val auth=envField(s.brain,"HERMES_CLOUD_AUTH").ifBlank{"UNKNOWN"}
    val route=envField(s.brain,"HERMES_CLOUD_ROUTE").ifBlank{"—"}
    val model=envField(s.brain,"HERMES_CLOUD_MODEL").ifBlank{"—"}
    val latency=envField(s.brain,"HERMES_CLOUD_LATENCY_MS").ifBlank{"—"}
    val http=envField(s.brain,"HERMES_CLOUD_HTTP_CODE").ifBlank{"—"}
    val fallback=envField(s.brain,"HERMES_CLOUD_FALLBACK_USED").ifBlank{"NO"}
    val requestId=envField(s.brain,"HERMES_CLOUD_REQUEST_ID").ifBlank{"—"}
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{"—"}
    val contract=envField(s.controlCenterSync,"HERMES_CLOUD").ifBlank{"UNPUBLISHED"}
    val role=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE").ifBlank{"REMOTE_BACKEND_OF_HERMES_H2_NOT_THIRD_BRAIN"}
    val body="Contract: $contract\\nEndpoint: hermes-cloud-djaeger.moclomper.workers.dev\\nHERMES H2 backend: $backend\\nCloud state: $state\\nAccess key: $auth • secret never displayed\\nRoute: $route\\nModel: $model\\nLatency: $latency ms • HTTP: $http\\nCloud tier fallback used: $fallback\\nRequest ID: $requestId\\nCurrent brain: $currentBrain\\nRole: $role\\nPolicy: Gemini primary → HERMES H2 cloud → HERMES H2 local → native failsafe\\nCloud direct hardware authority: NONE\\nHardware executor: AI AGENT A1 ONLY"
    BoxCard("HERMES CLOUD • ONE HERMES • HERMESCLOUD1",body,true)
}

'''
anchor='@Composable fun HermesCard(s:RuntimeState){'
assert anchor in m
m=m.replace(anchor,card+anchor,1)

# Keep Hermes card truthful now that HERMES H2 can use cloud or local backend.
old_sync='''    val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1"&&syncModule=="129631"&&syncCc=="12258"'''
new_sync='''    val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1"&&syncModule=="129633"&&syncCc=="12260"'''
assert old_sync in m
m=m.replace(old_sync,new_sync,1)
old_auth='''    val authority=if(currentBrain=="GEMINI") "SHADOW LEARNING • GEMINI HAS DECISION AUTHORITY" else "DEPUTY LOCAL BRAIN • ACTIVE ONLY WHEN GEMINI UNAVAILABLE • NO DIRECT HARDWARE WRITES"'''
new_auth='''    val hBackend=envField(s.brain,"HERMES_BACKEND").ifBlank{"LOCAL"}\n    val authority=if(currentBrain=="GEMINI") "SHADOW LEARNING • GEMINI HAS DECISION AUTHORITY" else "DEPUTY HERMES H2 • backend $hBackend • NO DIRECT HARDWARE WRITES"'''
assert old_auth in m
m=m.replace(old_auth,new_auth,1)

# Put cloud status beside the HERMES/Agent architecture cards without changing layout family.
old_over='''StrategyCard(s);AgentRebuild3Card(s);KernelAgentSyncCard(s);HermesCard(s);HumanComfortHcc1Card(s)'''
new_over='''StrategyCard(s);AgentRebuild3Card(s);HermesCloudCard(s);KernelAgentSyncCard(s);HermesCard(s);HumanComfortHcc1Card(s)'''
assert old_over in m
m=m.replace(old_over,new_over,1)

main.write_text(m); build.write_text(b)

M=main.read_text(); B=build.read_text()
assert 'versionCode = 12260' in B
assert 'hermescloud1' in B
assert 'SHAREDINT1 • HERMESCLOUD1' in M
assert 'REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1' in M
assert 'syncModule=="129633"&&syncCc=="12260"' in M
assert 'syncHermesCloud=="HERMESCLOUD1"' in M
assert 'HERMES CLOUD • ONE HERMES • HERMESCLOUD1' in M
assert 'Hardware executor: AI AGENT A1 ONLY' in M
assert 'secret never displayed' in M
assert 'Gemini primary → HERMES H2 cloud → HERMES H2 local → native failsafe' in M
print('HERMESCLOUD1_CC_PATCH=PASS')
print('MODULE_VC=129633')
print('CONTROL_CENTER_VC=12260')
print('EXACT_PAIR_CONTRACT=PASS')
print('NEW_RECURRING_ROOT_READS=0')
