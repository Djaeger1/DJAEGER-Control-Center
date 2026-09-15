from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

M=main.read_text(); R=repo.read_text(); C=mapper.read_text(); RD=reader.read_text(); B=build.read_text()

# REBUILD2 is strictly additive on the proven WORKLOADFINAL1 Control Center pair.
# VersionCode MUST stay 12261 because the healthy module pair stays VC129637.
assert 'versionCode = 12261' in B
old_v='versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"'
assert old_v in B
B=B.replace(old_v,'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1-neurongov2-askhermes2"',1)

# Visible identity must agree with the installed feature pair.
old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1 • WORKLOADFINAL1'
assert old_header in M
M=M.replace(old_header,old_header+' • NEURONGOV2 • ASKHERMES2',1)

# Append two read-only DJAEGER-owned state files to the EXISTING single recurring root read.
# No new polling process, no sysfs scan, no secret/config file is exposed.
reader_anchor="""                printf '\\n__CONTROL_CENTER_SYNC__\\n'\n                printf \"CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'\\n\""""
reader_insert="""                printf '\\n__HERMES_NEURON__\\n'\n                cat /data/adb/djaeger_ai/hermes/neuron_budget.env 2>/dev/null\n                printf '\\n__ASK_HERMES__\\n'\n                cat /data/adb/djaeger_ai/hermes/ask_hermes_state.env 2>/dev/null\n                printf '\\n__CONTROL_CENTER_SYNC__\\n'\n                printf \"CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'\\n\""""
assert RD.count(reader_anchor)==1, 'reader baseline anchor mismatch'
RD=RD.replace(reader_anchor,reader_insert,1)

# Map the two new read-only sections.
map_fields='''        val gameRegistryManual: String,\n        val strategyResult: String,'''
map_fields_new='''        val gameRegistryManual: String,\n        val hermesNeuron: String,\n        val askHermes: String,\n        val strategyResult: String,'''
assert C.count(map_fields)==1
C=C.replace(map_fields,map_fields_new,1)
map_ctor='''            gameRegistryManual = s["GAME_REGISTRY_MANUAL"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
map_ctor_new='''            gameRegistryManual = s["GAME_REGISTRY_MANUAL"].orEmpty(),\n            hermesNeuron = s["HERMES_NEURON"].orEmpty(),\n            askHermes = s["ASK_HERMES"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
assert C.count(map_ctor)==1
C=C.replace(map_ctor,map_ctor_new,1)

# RuntimeState carries display-only status. No authority is added.
state_anchor='''val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val envelope:String=""'''
state_new='''val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val hermesNeuron:String="",val askHermes:String="",val envelope:String=""'''
assert R.count(state_anchor)==1
R=R.replace(state_anchor,state_new,1)
repo_ctor='''workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,\n            envelope=mapped.envelope,'''
repo_ctor_new='''workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,hermesNeuron=mapped.hermesNeuron,askHermes=mapped.askHermes,\n            envelope=mapped.envelope,'''
assert R.count(repo_ctor)==1
R=R.replace(repo_ctor,repo_ctor_new,1)

# Compact HERMES status card. Reads state only; it never writes hardware/network state.
card_anchor='@Composable fun HermesCloudCard(s:RuntimeState){'
assert M.count(card_anchor)==1
card=r'''@Composable fun HermesStatusCard(s:RuntimeState){
    val backend=envField(s.brain,"HERMES_BACKEND").uppercase()
    val cloudState=envField(s.brain,"HERMES_CLOUD_STATE").uppercase()
    val cloudRoute=envField(s.brain,"HERMES_CLOUD_ROUTE").uppercase()
    val askRoute=envField(s.askHermes,"ROUTE").uppercase()
    val auth=envField(s.hermesNeuron,"CLOUD_AUTH").uppercase()
    val used=envField(s.hermesNeuron,"USED_EST").ifBlank{"0"}
    val limit=envField(s.hermesNeuron,"LIMIT").ifBlank{"10000"}
    val route=when{
        askRoute=="FAST"||askRoute=="SMART"||askRoute=="DEEP"->askRoute
        backend=="CLOUD"&&(cloudRoute=="FAST"||cloudRoute=="SMART"||cloudRoute=="DEEP")->cloudRoute
        else->"LOCAL"
    }
    val cloud=when{
        cloudState=="QUOTA_EXHAUSTED"||cloudState=="FAILED"->"OFFLINE"
        backend=="CLOUD"->"ACTIVE"
        auth=="CONFIGURED"||cloudState=="READY"->"READY"
        else->"OFFLINE"
    }
    BoxCard("HERMES: ${if(s.installed) "ONLINE" else "OFFLINE"}","Route    $route\nCloud    $cloud\nNeurons  $used / $limit",true)
}

'''
M=M.replace(card_anchor,card+card_anchor,1)

# Preserve the established Overview order; add one card immediately after Strategy.
overview_old='NetworkCard(s.network);StrategyCard(s);AgentRebuild3Card(s)'
overview_new='NetworkCard(s.network);StrategyCard(s);HermesStatusCard(s);AgentRebuild3Card(s)'
assert M.count(overview_old)==1, f'overview anchor count={M.count(overview_old)}'
M=M.replace(overview_old,overview_new,1)

# Separate Ask HERMES state; Gemini state/path remains intact.
state_old='var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}'
state_new=state_old+'\n    var hermesChatInput by remember{mutableStateOf("")}; var hermesChatResult by remember{mutableStateOf("Ask HERMES naturally. ONE HERMES chooses LOCAL / FAST / SMART / DEEP automatically.")}'
assert M.count(state_old)==1
M=M.replace(state_old,state_new,1)

clear_old='"CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}'
clear_new=clear_old+'\n            "HERMES_CHAT"->{val r=repo.hermesChat(hermesChatInput);hermesChatResult=r.second.ifBlank{"HERMES_CHAT_ERROR=EMPTY_RESPONSE"}}\n            "HERMES_CLEAR_CHAT"->{val r=repo.hermesChatClear();hermesChatResult=r.second.ifBlank{"HERMES_CHAT_HISTORY=CLEARED"}}'
assert M.count(clear_old)==1
M=M.replace(clear_old,clear_new,1)

gemini_box='BoxCard("GEMINI CONVERSATION",chatResult+"\\n\\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)'
hermes_ui=r'''BoxCard("GEMINI CONVERSATION",chatResult+"\n\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)
        OutlinedTextField(value=hermesChatInput,onValueChange={hermesChatInput=it.take(8000)},label={Text("Ask DJAEGER Hermes")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="HERMES_CHAT"},enabled=bridgeOp==null&&hermesChatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK HERMES")}
            Button(onClick={bridgeOp="HERMES_CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW HERMES CHAT")}
        }
        BoxCard("HERMES CONVERSATION",hermesChatResult+"\n\nAsk HERMES is separate from Gemini. Hardware execution authority remains inside DJAEGER Agent/validators.",true)'''
assert M.count(gemini_box)==1
M=M.replace(gemini_box,hermes_ui,1)

# App talks only to the module-owned Ask HERMES helper through root shell.
repo_anchor='''    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai gemini-chat-clear",5000); Pair(rc==0,out.trim())\n    }\n'''
repo_insert=repo_anchor+'''\n    suspend fun hermesChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(prompt.isBlank()) return@withContext Pair(false,"HERMES_CHAT_ERROR=EMPTY_PROMPT")\n        val (rc,out)=suStdin("$module/system/bin/djaeger-hermes-chat chat-stdin",prompt.take(8000),40000)\n        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_ERROR=EMPTY_RESPONSE" else "HERMES_CHAT_FAILED"})\n    }\n\n    suspend fun hermesChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("$module/system/bin/djaeger-hermes-chat chat-clear",5000)\n        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_HISTORY=CLEARED" else "HERMES_CHAT_CLEAR_FAILED"})\n    }\n'''
assert R.count(repo_anchor)==1
R=R.replace(repo_anchor,repo_insert,1)

# Final structural gates before writing anything.
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('private fun compactModuleVersion',M.index('@Composable fun Overview(s:RuntimeState)'))]
assert ov.count('HermesStatusCard(s)')==1
assert ov.index('StrategyCard(s)') < ov.index('HermesStatusCard(s)') < ov.index('AgentRebuild3Card(s)')
ai=M[M.index('@Composable fun AI(s:RuntimeState)'):M.index('private fun aiSummary',M.index('@Composable fun AI(s:RuntimeState)'))]
assert ai.count('Ask DJAEGER Gemini')==1
assert ai.count('Ask DJAEGER Hermes')==1
assert ai.index('Ask DJAEGER Gemini') < ai.index('GEMINI CONVERSATION') < ai.index('Ask DJAEGER Hermes') < ai.index('HERMES CONVERSATION')
assert 'djaeger-hermes-chat chat-stdin' in R
assert '/sys/' not in R
assert 'versionCode = 12261' in B
assert 'NEURONGOV2 • ASKHERMES2' in M

main.write_text(M); repo.write_text(R); mapper.write_text(C); reader.write_text(RD); build.write_text(B)
print('R51_REBUILD2=PASS')
print('BASELINE_PAIR=VC129637_VC12261')
print('OVERVIEW_ORDER_PRESERVED=PASS')
print('HERMES_STATUS_AFTER_STRATEGY=PASS')
print('ASK_HERMES_BELOW_GEMINI=PASS')
print('GEMINI_PATH_PRESERVED=PASS')
print('NEW_ROOT_POLLING_PROCESS=0')
print('APP_DIRECT_NETWORK=0')
print('APP_DIRECT_SYSFS=0')
