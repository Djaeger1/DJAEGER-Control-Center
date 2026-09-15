from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); rd=reader.read_text(); b=build.read_text()

# Pair identity: APPCONTROL1 RC1 module VC129638 + Control Center VC12262.
assert 'versionCode = 12261' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"' in b
b=b.replace('versionCode = 12261','versionCode = 12262',1)
b=b.replace(
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"',
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1-appcontrol1-rc1"',1)

# Extend RuntimeState with first-class APP / subject / workload-domain fields from runtime_status.
old='val active:String="0",val game:String="NA",val window:String="INACTIVE"'
new='val active:String="0",val game:String="NA",val app:String="NA",val subjectPackage:String="NA",val workloadClass:String="IDLE",val window:String="INACTIVE"'
assert old in r
r=r.replace(old,new,1)
old='''            game=if(sessionFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            window=if(sessionFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",'''
new='''            game=if(sessionFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            app=if(sessionFresh) (rt["APP"] ?: rt["app"] ?: "NA") else "NA",\n            subjectPackage=if(sessionFresh) (rt["SUBJECT_PACKAGE"] ?: rt["subject_package"] ?: (rt["GAME"] ?: rt["game"] ?: "NA")) else "NA",\n            workloadClass=if(sessionFresh) (rt["WORKLOAD_CLASS"] ?: rt["workload_class"] ?: if((rt["GAME"] ?: rt["game"] ?: "NA")!="NA") "GAME" else "IDLE") else "IDLE",\n            window=if(sessionFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",'''
assert old in r
r=r.replace(old,new,1)

# Consolidated root-read self-identifies the new pair; still one recurring root process.
rd=rd.replace("CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'",
              "CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1_APPCONTROL1'",1)
rd=rd.replace("MODULE_VERSION_CODE='129637'","MODULE_VERSION_CODE='129638'",1)
rd=rd.replace("CONTROL_CENTER_VERSION_CODE='12261'","CONTROL_CENTER_VERSION_CODE='12262'",1)
anchor='''                printf "PREEXEC_WORKLOAD_GUARD='ACTIVE'\\n"\n                printf "WORKLOAD_DATA_SOURCE='SINGLE_ROOT_READ_DJAEGER_STATE'\\n"'''
insert='''                printf "PREEXEC_WORKLOAD_GUARD='ACTIVE'\\n"\n                printf "APPCONTROL='APPCONTROL1_RC1'\\n"\n                printf "WORKLOAD_SESSION_CLASSES='GAME_APP_SYSTEM'\\n"\n                printf "GAME_REGISTRY='GAME_ONLY'\\n"\n                printf "APP_REGISTRY='EXPLICIT_APP_ONLY'\\n"\n                printf "APP_CONTROL='BOUNDED_PROFILE_ONLY'\\n"\n                printf "APP_EXECUTION_OWNER='AI_AGENT_A1_ONLY'\\n"\n                printf "MEMORY_ISOLATION='WORKLOAD_CLASS_PACKAGE_SESSION'\\n"\n                printf "WORKLOAD_DATA_SOURCE='SINGLE_ROOT_READ_DJAEGER_STATE'\\n"'''
assert anchor in rd
rd=rd.replace(anchor,insert,1)

# Header identity only; preserve the established Overview ordering.
header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1 • WORKLOADFINAL1'
assert header in m
m=m.replace(header,header+' • APPCONTROL1',1)

# Shared helpers for truthful GAME / APP / SYSTEM session presentation.
insert_at=m.index('@Composable fun ThoughtsCard')
helpers=r'''private fun effectiveWorkloadClass(s:RuntimeState):String = s.workloadClass.ifBlank{envField(s.workloadContext,"WORKLOAD_CLASS")}.ifBlank{"IDLE"}
private fun effectiveSubject(s:RuntimeState):String{
    val raw=s.subjectPackage.ifBlank{envField(s.workloadContext,"SUBJECT_PACKAGE")}
    if(raw.isNotBlank()&&raw!="NA"&&raw!="UNKNOWN")return raw
    return when(effectiveWorkloadClass(s)){"APP"->s.app;"GAME"->s.game;else->"NA"}
}
private fun sessionSubjectLabel(s:RuntimeState):String = when(effectiveWorkloadClass(s)){
    "APP"->"App: ${effectiveSubject(s)}"
    "GAME"->"Game: ${effectiveSubject(s)}"
    "SYSTEM"->"System: ${effectiveSubject(s)}"
    else->"Subject: —"
}
'''
m=m[:insert_at]+helpers+'\n'+m[insert_at:]

# Replace only the ENGINE / SESSION card. APPCONTROL1 must never call an APP a game.
a=m.index('@Composable fun StatusCard(s:RuntimeState)')
bidx=m.index('@Composable fun ThermalRow',a)
status=r'''@Composable fun StatusCard(s:RuntimeState){
    val stale=runtimeStateStale(s)
    val session=when{ s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"}
    val wc=effectiveWorkloadClass(s)
    val stateLabel=when{ s.active=="1"&&wc=="GAME"->"GAME ACTIVE";s.active=="1"&&wc=="APP"->"APP ACTIVE";s.active=="1"->"ACTIVE";else->"IDLE"}
    val appExec=when{ s.active=="1"&&wc=="APP"->"ALLOWED / BOUNDED PROFILE";wc=="SYSTEM"->"BLOCKED";else->"—"}
    val gameExec=when{ s.active=="1"&&wc=="GAME"->"ALLOWED";else->"BLOCKED"}
    val body=if(s.installed) "Engine: ${if(stale)"STALE" else "LIVE"}\\nSession: $stateLabel\\nModule: ${s.moduleVersion}\\n${sessionSubjectLabel(s)}\\nWorkload: $wc • ${effectiveSubject(s)}\\nWindow: ${s.window}\\nProfile: ${s.telemetry.profile}\\nAPP execution: $appExec\\nGame execution: $gameExec\\nLast device sample: $session\\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found"
    BoxCard("ENGINE / SESSION",body)
}
'''
m=m[:a]+status+'\n'+m[bidx:]

# Session monitor uses the canonical subject label, not the legacy GAME field.
m=m.replace('Window: ${s.window} • Game: ${s.game}\\nObserved phase:', 'Window: ${s.window} • ${sessionSubjectLabel(s)}\\nObserved phase:',1)

# Agent matched-pair truth.
old_contract='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'
new_contract=old_contract+'_APPCONTROL1'
m=m.replace(old_contract,new_contract)
m=m.replace('syncModule=="129637"&&syncCc=="12261"','syncModule=="129638"&&syncCc=="12262"')

# Replace workload card with APPCONTROL semantics while preserving its exact Overview position.
a=m.index('@Composable fun WorkloadIntelligenceCard(s:RuntimeState)')
bidx=m.index('@Composable fun DualRegistrySummaryCard',a)
workload=r'''@Composable fun WorkloadIntelligenceCard(s:RuntimeState){
    val pkg=envField(s.workloadContext,"PACKAGE").ifBlank{effectiveSubject(s)}
    val cls=envField(s.workloadContext,"WORKLOAD_CLASS").ifBlank{effectiveWorkloadClass(s)}
    val profile=envField(s.workloadContext,"WORKLOAD_PROFILE").ifBlank{"UNKNOWN"}
    val domain=envField(s.workloadContext,"REASONING_DOMAIN").ifBlank{cls}
    val source=envField(s.workloadContext,"SOURCE").ifBlank{"RUNTIME"}
    val confidence=envField(s.workloadContext,"CONFIDENCE").ifBlank{"0"}
    val eligible=envField(s.workloadContext,"CONTROL_ELIGIBLE").ifBlank{"NO"}
    val appEligible=envField(s.workloadContext,"APP_CONTROL_ELIGIBLE").ifBlank{"NO"}
    val finalState=envField(s.workloadFinal,"STATUS").ifBlank{"UNAVAILABLE"}
    val execScope=envField(s.workloadFinal,"EXECUTION_SCOPE").ifBlank{"UNAVAILABLE"}
    val appControl=envField(s.workloadFinal,"APP_CONTROL").ifBlank{"UNAVAILABLE"}
    val appEligibility=envField(s.workloadFinal,"APP_ELIGIBILITY").ifBlank{"UNAVAILABLE"}
    val systemPolicy=envField(s.workloadFinal,"SYSTEM_POLICY").ifBlank{"UNAVAILABLE"}
    val learning=envField(s.workloadFinal,"LEARNING_ISOLATION").ifBlank{"UNAVAILABLE"}
    val owner=envField(s.workloadFinal,"EXECUTION_OWNER").ifBlank{"UNAVAILABLE"}
    val guardDecision=envField(s.workloadExecGuard,"DECISION").ifBlank{"IDLE"}
    val guardReason=envField(s.workloadExecGuard,"REASON").ifBlank{"—"}
    val syncContract=envField(s.controlCenterSync,"CONTRACT")
    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE")
    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE")
    val paired=syncContract.endsWith("APPCONTROL1")&&syncModule=="129638"&&syncCc=="12262"&&finalState=="ACTIVE"
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{"—"}
    val brain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"BRAIN_SOURCE").ifBlank{"—"}}
    val body="Current: $cls • $pkg\\nProfile: $profile • Reasoning domain: $domain\\nClassifier: $source • confidence $confidence%\\nControl eligible: $eligible • APP eligible: $appEligible\\n\\nActive brain: $brain\\nBrain mode: $brainMode\\nExecution scope: $execScope\\nAPP control: $appControl\\nAPP eligibility: $appEligibility\\nSYSTEM policy: $systemPolicy\\nExecution owner: $owner\\nLearning isolation: $learning\\nPre-exec guard: $guardDecision • $guardReason\\n\\nControl Center pair: ${if(paired)"MATCHED • VC129638 / VC12262" else "CHECKING / NOT MATCHED"}"
    BoxCard("WORKLOAD • GAME / APP / SYSTEM",body,true)
}
'''
m=m[:a]+workload+'\n'+m[bidx:]

# Add APPCONTROL-specific authority lines to Agent card if not already present.
needle='''    val syncPreexecGuard=envField(s.controlCenterSync,"PREEXEC_WORKLOAD_GUARD")\n'''
assert needle in m
m=m.replace(needle, needle+'''    val syncAppControl=envField(s.controlCenterSync,"APP_CONTROL")\n    val syncAppOwner=envField(s.controlCenterSync,"APP_EXECUTION_OWNER")\n    val syncMemoryIsolation=envField(s.controlCenterSync,"MEMORY_ISOLATION")\n''',1)
bodyneedle='''Pre-exec workload guard: ${syncPreexecGuard.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts:'''
assert bodyneedle in m
m=m.replace(bodyneedle,'''Pre-exec workload guard: ${syncPreexecGuard.ifBlank{"UNPUBLISHED"}}\\nAPP control: ${syncAppControl.ifBlank{"UNPUBLISHED"}}\\nAPP execution owner: ${syncAppOwner.ifBlank{"UNPUBLISHED"}}\\nMemory isolation: ${syncMemoryIsolation.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts:''',1)

# Hard gates: semantics and layout must be truthful, no UI control authority added.
assert 'Session: $stateLabel' in m
assert 'APP ACTIVE' in m and 'GAME ACTIVE' in m
assert 'APP execution: $appExec' in m and 'Game execution: $gameExec' in m
assert 'APP control: $appControl' in m
assert 'VC129638 / VC12262' in m
assert new_contract in m
assert ' • APPCONTROL1' in m
assert 'ProcessBuilder("su"' not in m  # UI composition remains read-only; root I/O stays repository/reader owned.
assert rd.count('ProcessBuilder("su"') == 1
assert '/sys/' not in rd and '/proc/sys/' not in rd

main.write_text(m); repo.write_text(r); reader.write_text(rd); build.write_text(b)
print('APPCONTROL1_UI_PATCH=PASS')
print('CONTROL_CENTER_VC=12262')
print('MATCHED_MODULE_VC=129638')
print('GAME_APP_SYSTEM_SESSION_TRUTH=PASS')
print('APP_BOUNDED_CONTROL_UI=PASS')
print('SINGLE_RECURRING_ROOT_READ=PRESERVED')
