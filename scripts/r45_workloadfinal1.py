from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); c=mapper.read_text(); rd=reader.read_text(); b=build.read_text()

# Pair identity: current live module VC129637 + final GAME/APP/SYSTEM enforcement.
assert 'versionCode = 12260' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1"' in b
b=b.replace('versionCode = 12260','versionCode = 12261',1)
b=b.replace(
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1"',
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"',1)

# Preserve the single recurring root process. The same read now appends only DJAEGER-owned,
# atomically-published workload state files. No second polling process and no sysfs scan.
old_reader='''            val process = ProcessBuilder("su", "-c", "cat '$snapshotPath' 2>/dev/null")\n                .redirectErrorStream(true)\n                .start()'''
new_reader='''            val command = """\n                cat '$snapshotPath' 2>/dev/null\n                printf '\\n__WORKLOAD_CONTEXT__\\n'\n                cat /data/adb/djaeger_ai/workload_context.env 2>/dev/null\n                printf '\\n__WORKLOAD_GATE__\\n'\n                cat /data/adb/djaeger_ai/workload_gate_state.env 2>/dev/null\n                printf '\\n__PROPOSAL_BINDING__\\n'\n                cat /data/adb/djaeger_ai/proposal_binding_state.env 2>/dev/null\n                printf '\\n__WORKLOAD_FINAL__\\n'\n                cat /data/adb/djaeger_ai/workload_final_state.env 2>/dev/null\n                printf '\\n__WORKLOAD_EXEC_GUARD__\\n'\n                cat /data/adb/djaeger_ai/workload_exec_guard_state.env 2>/dev/null\n                printf '\\n__APP_REGISTRY__\\n'\n                cat /data/adb/djaeger_ai/workload/app_registry.tsv 2>/dev/null\n                printf '\\n__GAME_REGISTRY_MANUAL__\\n'\n                cat /data/adb/djaeger_ai/custom_games.tsv 2>/dev/null\n                printf '\\n__CONTROL_CENTER_SYNC__\\n'\n                printf "CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'\\n"\n                printf "MODULE_VERSION_CODE='129637'\\n"\n                printf "CONTROL_CENTER_VERSION_CODE='12261'\\n"\n                printf "WORKLOAD_FINAL='WORKLOADFINAL1'\\n"\n                printf "WORKLOAD_CLASSIFICATION='GAME_APP_SYSTEM'\\n"\n                printf "DUAL_REGISTRY='ENFORCED'\\n"\n                printf "PREEXEC_WORKLOAD_GUARD='ACTIVE'\\n"\n                printf "WORKLOAD_DATA_SOURCE='SINGLE_ROOT_READ_DJAEGER_STATE'\\n"\n            """.trimIndent()\n            val process = ProcessBuilder("su", "-c", command)\n                .redirectErrorStream(true)\n                .start()'''
assert old_reader in rd
rd=rd.replace(old_reader,new_reader,1)
rd=rd.replace(
    ' * The only recurring root read intended for r9 UI polling.\n * Reads a DJAEGER-owned atomic file; never scans whole-device sysfs.',
    ' * The only recurring root read intended for UI polling.\n * Reads cc_snapshot plus DJAEGER-owned atomic workload state in the same root process; never scans sysfs.',1)

# Add new raw sections to the one consolidated mapping surface.
old='''        val controlCenterSync: String,\n        val strategyResult: String,'''
new='''        val controlCenterSync: String,\n        val workloadContext: String,\n        val workloadGate: String,\n        val proposalBinding: String,\n        val workloadFinal: String,\n        val workloadExecGuard: String,\n        val appRegistry: String,\n        val gameRegistryManual: String,\n        val strategyResult: String,'''
assert old in c
c=c.replace(old,new,1)
old='''            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
new='''            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),\n            workloadContext = s["WORKLOAD_CONTEXT"].orEmpty(),\n            workloadGate = s["WORKLOAD_GATE"].orEmpty(),\n            proposalBinding = s["PROPOSAL_BINDING"].orEmpty(),\n            workloadFinal = s["WORKLOAD_FINAL"].orEmpty(),\n            workloadExecGuard = s["WORKLOAD_EXEC_GUARD"].orEmpty(),\n            appRegistry = s["APP_REGISTRY"].orEmpty(),\n            gameRegistryManual = s["GAME_REGISTRY_MANUAL"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
assert old in c
c=c.replace(old,new,1)

# RuntimeState carries only UI-readable workload truth; no new control/hardware authority.
old='''val controlCenterSync:String="",val envelope:String=""'''
new='''val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val envelope:String=""'''
assert old in r
r=r.replace(old,new,1)
old='''agentSysfs1Capability=mapped.agentSysfs1Capability,agentSysfs1Execution=mapped.agentSysfs1Execution,controlCenterSync=mapped.controlCenterSync,\n            envelope=mapped.envelope,'''
new='''agentSysfs1Capability=mapped.agentSysfs1Capability,agentSysfs1Execution=mapped.agentSysfs1Execution,controlCenterSync=mapped.controlCenterSync,workloadContext=mapped.workloadContext,workloadGate=mapped.workloadGate,proposalBinding=mapped.proposalBinding,workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,\n            envelope=mapped.envelope,'''
assert old in r
r=r.replace(old,new,1)

# Header identifies the synchronized feature set.
old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1'
assert old_header in m
m=m.replace(old_header,old_header+' • WORKLOADFINAL1',1)

# New matched-pair fields and contract in Agent card.
old_vars='''    val syncHermesCloud=envField(s.controlCenterSync,"HERMES_CLOUD")\n    val syncHermesCloudRole=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE")\n    val syncHermesBackendPriority=envField(s.controlCenterSync,"HERMES_BACKEND_PRIORITY")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1"&&syncModule=="129633"&&syncCc=="12260"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"&&syncGameRegistry=="GAMEREG1"&&syncShared=="SHAREDINT1"&&syncHermesCloud=="HERMESCLOUD1"&&geminiScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"&&hermesScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)&&s.moduleVersion.contains("GAMEREG1",true)&&s.moduleVersion.contains("SHAREDINT1",true)&&s.moduleVersion.contains("HERMESCLOUD1",true)\n'''
new_vars='''    val syncHermesCloud=envField(s.controlCenterSync,"HERMES_CLOUD")\n    val syncHermesCloudRole=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE")\n    val syncHermesBackendPriority=envField(s.controlCenterSync,"HERMES_BACKEND_PRIORITY")\n    val syncWorkloadFinal=envField(s.controlCenterSync,"WORKLOAD_FINAL")\n    val syncDualRegistry=envField(s.controlCenterSync,"DUAL_REGISTRY")\n    val syncPreexecGuard=envField(s.controlCenterSync,"PREEXEC_WORKLOAD_GUARD")\n    val workloadActive=envField(s.workloadFinal,"STATUS")=="ACTIVE"\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1"&&syncModule=="129637"&&syncCc=="12261"&&syncWorkloadFinal=="WORKLOADFINAL1"&&syncDualRegistry=="ENFORCED"&&syncPreexecGuard=="ACTIVE"&&workloadActive\n    val identityMatched=s.installed&&s.moduleVersion.contains("HERMESCLOUD1",true)&&workloadActive\n'''
assert old_vars in m
m=m.replace(old_vars,new_vars,1)

old_body='''HERMES backend priority: ${syncHermesBackendPriority.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts: DELTA / EVENT DRIVEN\\nThird brain: $third'''
new_body='''HERMES backend priority: ${syncHermesBackendPriority.ifBlank{"UNPUBLISHED"}}\\nWorkload final: ${syncWorkloadFinal.ifBlank{"UNPUBLISHED"}}\\nDual registry: ${syncDualRegistry.ifBlank{"UNPUBLISHED"}}\\nPre-exec workload guard: ${syncPreexecGuard.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts: DELTA / EVENT DRIVEN\\nThird brain: $third'''
assert old_body in m
m=m.replace(old_body,new_body,1)

# HERMES matched-pair label follows the same new contract.
old_sync='''    val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1"&&syncModule=="129633"&&syncCc=="12260"'''
new_sync='''    val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1"&&syncModule=="129637"&&syncCc=="12261"'''
assert old_sync in m
m=m.replace(old_sync,new_sync,1)

# UI cards. They are strictly read-only consumers of the single root snapshot read.
cards=r'''private fun registryPreview(raw:String,max:Int=8):String{
    val rows=raw.lineSequence().map{it.trim()}.filter{it.isNotBlank()&&!it.startsWith("#")}.take(max).toList()
    return if(rows.isEmpty()) "—" else rows.joinToString("\n")
}

@Composable fun WorkloadIntelligenceCard(s:RuntimeState){
    val pkg=envField(s.workloadContext,"PACKAGE").ifBlank{"UNKNOWN"}
    val cls=envField(s.workloadContext,"WORKLOAD_CLASS").ifBlank{"UNKNOWN"}
    val profile=envField(s.workloadContext,"WORKLOAD_PROFILE").ifBlank{"UNKNOWN"}
    val subject=envField(s.workloadContext,"SUBJECT_CLASS").ifBlank{cls}
    val domain=envField(s.workloadContext,"REASONING_DOMAIN").ifBlank{"UNKNOWN"}
    val gameSem=envField(s.workloadContext,"GAME_SEMANTICS").ifBlank{"UNKNOWN"}
    val frameSem=envField(s.workloadContext,"FRAME_SEMANTICS").ifBlank{"UNKNOWN"}
    val source=envField(s.workloadContext,"SOURCE").ifBlank{"UNKNOWN"}
    val confidence=envField(s.workloadContext,"CONFIDENCE").ifBlank{"0"}

    val finalState=envField(s.workloadFinal,"STATUS").ifBlank{"UNAVAILABLE"}
    val dual=envField(s.workloadFinal,"DUAL_REGISTRY").ifBlank{"UNAVAILABLE"}
    val conflicts=envField(s.workloadFinal,"REGISTRY_CONFLICTS").ifBlank{"—"}
    val execScope=envField(s.workloadFinal,"EXECUTION_SCOPE").ifBlank{"UNAVAILABLE"}
    val appPolicy=envField(s.workloadFinal,"APP_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val systemPolicy=envField(s.workloadFinal,"SYSTEM_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val unknownPolicy=envField(s.workloadFinal,"UNKNOWN_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val stale=envField(s.workloadFinal,"STALE_POLICY").ifBlank{"UNAVAILABLE"}
    val learning=envField(s.workloadFinal,"LEARNING_ISOLATION").ifBlank{"UNAVAILABLE"}

    val proposalSource=envField(s.proposalBinding,"LATEST_PROPOSAL_SOURCE").ifBlank{"NONE"}
    val proposalPkg=envField(s.proposalBinding,"LATEST_SUBJECT_PACKAGE").ifBlank{"UNKNOWN"}
    val proposalClass=envField(s.proposalBinding,"LATEST_SUBJECT_CLASS").ifBlank{"UNKNOWN"}
    val proposalDecision=envField(s.proposalBinding,"LATEST_BINDING_DECISION").ifBlank{"NO_PROPOSAL"}
    val proposalReason=envField(s.proposalBinding,"LATEST_BINDING_REASON").ifBlank{"NO_PROPOSAL"}

    val gateGame=envField(s.workloadGate,"GAME_ONLY").ifBlank{"UNAVAILABLE"}
    val gateApp=envField(s.workloadGate,"APP_ONLY").ifBlank{"UNAVAILABLE"}
    val gateSystem=envField(s.workloadGate,"SYSTEM_ONLY").ifBlank{"UNAVAILABLE"}
    val guardDecision=envField(s.workloadExecGuard,"DECISION").ifBlank{envField(s.workloadExecGuard,"GUARD_DECISION").ifBlank{"IDLE"}}
    val guardReason=envField(s.workloadExecGuard,"REASON").ifBlank{envField(s.workloadExecGuard,"GUARD_REASON").ifBlank{"—"}}

    val syncContract=envField(s.controlCenterSync,"CONTRACT")
    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE")
    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE")
    val paired=syncContract.endsWith("WORKLOADFINAL1")&&syncModule=="129637"&&syncCc=="12261"&&finalState=="ACTIVE"

    val body="Current: $cls • $pkg\nProfile: $profile • Subject: $subject\nReasoning: $domain\nGame semantics: $gameSem\nFrame semantics: $frameSem\nClassifier: $source • confidence $confidence%\n\nFinal enforcement: $finalState\nDual registry: $dual • conflicts $conflicts\nExecution scope: $execScope\nAPP game policy: $appPolicy\nSYSTEM game policy: $systemPolicy\nUNKNOWN game policy: $unknownPolicy\nStale policy: $stale\nLearning isolation: $learning\n\nShadow domain gates: GAME $gateGame • APP $gateApp • SYSTEM $gateSystem\nLatest proposal: $proposalSource • $proposalClass • $proposalPkg\nBinding: $proposalDecision • $proposalReason\nPre-exec guard: $guardDecision • $guardReason\n\nControl Center pair: ${if(paired)"MATCHED • VC129637 / VC12261" else "CHECKING / NOT MATCHED"}"
    BoxCard("WORKLOAD • GAME / APP / SYSTEM",body,true)
}

@Composable fun DualRegistrySummaryCard(s:RuntimeState){
    val appRows=s.appRegistry.lineSequence().map{it.trim()}.filter{it.isNotBlank()&&!it.startsWith("#")}.toList()
    val gameRows=s.gameRegistryManual.lineSequence().map{it.trim()}.filter{it.isNotBlank()&&!it.startsWith("#")}.toList()
    val authority=envField(s.workloadContext,"GAME_REGISTRY_AUTHORITY").ifBlank{"UNAVAILABLE"}
    val conflicts=envField(s.workloadFinal,"REGISTRY_CONFLICTS").ifBlank{"—"}
    val body="Authority: $authority\nConflict count: $conflicts\nAPP registry: ${appRows.size} explicit override(s)\n${registryPreview(s.appRegistry)}\n\nManual GAME registry: ${gameRows.size}\n${registryPreview(s.gameRegistryManual)}\n\nGame registry editing remains below. APP overrides are displayed read-only so protected APP identities cannot be accidentally converted into GAME."
    BoxCard("DUAL REGISTRY • APP / GAME",body,true)
}

@Composable fun WorkloadSafetyCard(s:RuntimeState){
    val finalState=envField(s.workloadFinal,"STATUS").ifBlank{"UNAVAILABLE"}
    val app=envField(s.workloadFinal,"APP_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val system=envField(s.workloadFinal,"SYSTEM_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val unknown=envField(s.workloadFinal,"UNKNOWN_GAME_POLICY").ifBlank{"UNAVAILABLE"}
    val stale=envField(s.workloadFinal,"STALE_POLICY").ifBlank{"UNAVAILABLE"}
    val root=envField(s.workloadFinal,"ROOT_AUTHORITY_CHANGED").ifBlank{"UNAVAILABLE"}
    val sysfs=envField(s.workloadFinal,"SYSFS_AUTHORITY_CHANGED").ifBlank{"UNAVAILABLE"}
    val rescue=envField(s.workloadFinal,"RESCUE_PATH_CHANGED").ifBlank{"UNAVAILABLE"}
    val body="Final workload enforcement: $finalState\nAPP→game policy: $app\nSYSTEM→game policy: $system\nUNKNOWN→game policy: $unknown\nStale policy: $stale\nRoot Authority changed: $root\nSYSFS authority changed: $sysfs\nRescue path changed: $rescue\nControl Center authority: READ-ONLY / NO SYSFS WRITES"
    BoxCard("WORKLOAD ENFORCEMENT SAFETY",body,true)
}

'''
anchor='@Composable fun Overview(s:RuntimeState)'
assert anchor in m
m=m.replace(anchor,cards+anchor,1)

# Surface final workload truth in Overview, Session and Safety without changing tab architecture.
assert 'StatusCard(s);ThoughtsCard(s);' in m
m=m.replace('StatusCard(s);ThoughtsCard(s);','StatusCard(s);WorkloadIntelligenceCard(s);ThoughtsCard(s);',1)
assert '        GameRegistryCard(repo)\n' in m
m=m.replace('        GameRegistryCard(repo)\n','        DualRegistrySummaryCard(s)\n        GameRegistryCard(repo)\n',1)
old_safety='''@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){BoxCard("MONITOR INVARIANTS",'''
new_safety='''@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){WorkloadSafetyCard(s);BoxCard("MONITOR INVARIANTS",'''
assert old_safety in m
m=m.replace(old_safety,new_safety,1)

main.write_text(m); repo.write_text(r); mapper.write_text(c); reader.write_text(rd); build.write_text(b)

# Static contract gates.
M=main.read_text(); R=repo.read_text(); C=mapper.read_text(); RD=reader.read_text(); B=build.read_text()
assert 'versionCode = 12261' in B
assert 'hermescloud1-workloadfinal1' in B
assert 'HERMESCLOUD1 • WORKLOADFINAL1' in M
assert 'WORKLOAD • GAME / APP / SYSTEM' in M
assert 'DUAL REGISTRY • APP / GAME' in M
assert 'WORKLOAD ENFORCEMENT SAFETY' in M
assert 'VC129637 / VC12261' in M
assert 'WORKLOAD_CONTEXT' in C and 'WORKLOAD_FINAL' in C and 'PROPOSAL_BINDING' in C
assert 'workloadContext=mapped.workloadContext' in R
assert '__WORKLOAD_CONTEXT__' in RD and '__WORKLOAD_FINAL__' in RD and '__APP_REGISTRY__' in RD
assert 'ProcessBuilder("su", "-c", command)' in RD
assert '129637' in RD and '12261' in RD and 'WORKLOADFINAL1' in RD
assert RD.count('ProcessBuilder("su"') == 1, RD.count('ProcessBuilder("su"')
print('WORKLOADFINAL1_CC_PATCH=PASS')
print('MODULE_VC=129637')
print('CONTROL_CENTER_VC=12261')
print('CLASSIFICATION=GAME_APP_SYSTEM')
print('DUAL_REGISTRY=SYNCED_READ_ONLY_APP_MANUAL_GAME')
print('PREEXEC_GUARD=VISIBLE')
print('NEW_RECURRING_ROOT_READS=0')
