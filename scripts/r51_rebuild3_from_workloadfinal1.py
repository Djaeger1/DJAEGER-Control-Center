from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

M=main.read_text(); R=repo.read_text(); C=mapper.read_text(); RD=reader.read_text(); B=build.read_text()

# This patch is valid ONLY on the exact published WORKLOADFINAL1 source.
assert 'versionCode = 12261' in B
old_v='versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"'
assert B.count(old_v)==1
B=B.replace(old_v,'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1-neurongov3-askhermes3"',1)

old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1 • WORKLOADFINAL1'
assert M.count(old_header)==1
M=M.replace(old_header,old_header+' • NEURONGOV3 • ASKHERMES3',1)

# Read two sanitized module-owned state files in the EXISTING single root snapshot process.
reader_anchor="""                printf '\\n__GAME_REGISTRY_MANUAL__\\n'\n                cat /data/adb/djaeger_ai/custom_games.tsv 2>/dev/null\n                printf '\\n__CONTROL_CENTER_SYNC__\\n'"""
reader_new="""                printf '\\n__GAME_REGISTRY_MANUAL__\\n'\n                cat /data/adb/djaeger_ai/custom_games.tsv 2>/dev/null\n                printf '\\n__HERMES_NEURON__\\n'\n                cat /data/adb/djaeger_ai/hermes/neuron_budget.env 2>/dev/null\n                printf '\\n__ASK_HERMES__\\n'\n                cat /data/adb/djaeger_ai/hermes/ask_hermes_state.env 2>/dev/null\n                printf '\\n__CONTROL_CENTER_SYNC__\\n'"""
assert RD.count(reader_anchor)==1
RD=RD.replace(reader_anchor,reader_new,1)
assert 'HERMES_ACCESS_KEY' not in reader_new

# Extend the existing mapper with display-only state.
map_fields='''        val gameRegistryManual: String,\n        val strategyResult: String,'''
map_fields_new='''        val gameRegistryManual: String,\n        val hermesNeuron: String,\n        val askHermes: String,\n        val strategyResult: String,'''
assert C.count(map_fields)==1
C=C.replace(map_fields,map_fields_new,1)
map_ctor='''            gameRegistryManual = s["GAME_REGISTRY_MANUAL"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
map_ctor_new='''            gameRegistryManual = s["GAME_REGISTRY_MANUAL"].orEmpty(),\n            hermesNeuron = s["HERMES_NEURON"].orEmpty(),\n            askHermes = s["ASK_HERMES"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'''
assert C.count(map_ctor)==1
C=C.replace(map_ctor,map_ctor_new,1)

# RuntimeState: additive fields only.
state_anchor='''val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val envelope:String=""'''
state_new='''val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val hermesNeuron:String="",val askHermes:String="",val envelope:String=""'''
assert R.count(state_anchor)==1
R=R.replace(state_anchor,state_new,1)
repo_ctor='''controlCenterSync=mapped.controlCenterSync,workloadContext=mapped.workloadContext,workloadGate=mapped.workloadGate,proposalBinding=mapped.proposalBinding,workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,\n            envelope=mapped.envelope,'''
repo_ctor_new='''controlCenterSync=mapped.controlCenterSync,workloadContext=mapped.workloadContext,workloadGate=mapped.workloadGate,proposalBinding=mapped.proposalBinding,workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,hermesNeuron=mapped.hermesNeuron,askHermes=mapped.askHermes,\n            envelope=mapped.envelope,'''
assert R.count(repo_ctor)==1
R=R.replace(repo_ctor,repo_ctor_new,1)

# Compact HERMES status. No duplicated long diagnostics and no authority change.
status_card=r'''@Composable fun HermesStatusCard(s:RuntimeState){
    val askStatus=envField(s.askHermes,"STATUS").uppercase()
    val askRoute=envField(s.askHermes,"ROUTE").uppercase()
    val backend=envField(s.brain,"HERMES_BACKEND").uppercase()
    val cloudRoute=envField(s.brain,"HERMES_CLOUD_ROUTE").uppercase()
    val cloudState=envField(s.brain,"HERMES_CLOUD_STATE").uppercase()
    val auth=envField(s.hermesNeuron,"CLOUD_AUTH").uppercase()
    val used=envField(s.hermesNeuron,"USED_EST").ifBlank{"0"}
    val limit=envField(s.hermesNeuron,"LIMIT").ifBlank{"10000"}
    val route=when{
        askStatus=="REQUESTING"&&(askRoute=="FAST"||askRoute=="SMART"||askRoute=="DEEP")->askRoute
        backend=="CLOUD"&&(cloudRoute=="FAST"||cloudRoute=="SMART"||cloudRoute=="DEEP")->cloudRoute
        else->"LOCAL"
    }
    val cloud=when{
        askStatus=="REQUESTING"||backend=="CLOUD"->"ACTIVE"
        cloudState=="QUOTA_EXHAUSTED"||cloudState=="FAILED"||auth=="NOT_CONFIGURED"->"OFFLINE"
        auth=="CONFIGURED"->"READY"
        else->"OFFLINE"
    }
    BoxCard("HERMES: ${if(s.installed)"ONLINE" else "OFFLINE"}","Route    $route\nCloud    $cloud\nNeurons  $used / $limit",true)
}

'''
status_anchor='private fun registryPreview(raw:String,max:Int=8):String{'
assert M.count(status_anchor)==1
M=M.replace(status_anchor,status_card+status_anchor,1)

# Exact requested location: immediately after existing Strategy, before the existing next card.
overview_old='NetworkCard(s.network);StrategyCard(s);AgentRebuild3Card(s)'
overview_new='NetworkCard(s.network);StrategyCard(s);HermesStatusCard(s);AgentRebuild3Card(s)'
assert M.count(overview_old)==1
M=M.replace(overview_old,overview_new,1)

# Separate Ask HERMES state, preserving Gemini state and handlers exactly.
ai_state='''    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}\n'''
assert M.count(ai_state)==1
M=M.replace(ai_state,ai_state+'''    var hermesChatInput by remember{mutableStateOf("")}; var hermesChatResult by remember{mutableStateOf("Ask HERMES naturally. ONE HERMES chooses LOCAL / FAST / SMART / DEEP automatically.")}\n''',1)

handler='''            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}\n'''
assert M.count(handler)==1
M=M.replace(handler,handler+'''            "HERMES_CHAT"->{val r=repo.hermesChat(hermesChatInput);hermesChatResult=r.second.ifBlank{"HERMES_CHAT_ERROR=EMPTY_RESPONSE"}}\n            "HERMES_CLEAR_CHAT"->{val r=repo.hermesChatClear();hermesChatResult=r.second.ifBlank{"HERMES_CHAT_HISTORY=CLEARED"}}\n''',1)

gemini_box='''        BoxCard("GEMINI CONVERSATION",chatResult+"\\n\\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)\n'''
assert M.count(gemini_box)==1
hermes_ui=r'''        OutlinedTextField(value=hermesChatInput,onValueChange={hermesChatInput=it.take(8000)},label={Text("Ask DJAEGER Hermes")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="HERMES_CHAT"},enabled=bridgeOp==null&&hermesChatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK HERMES")}
            Button(onClick={bridgeOp="HERMES_CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW HERMES CHAT")}
        }
        BoxCard("HERMES CONVERSATION",hermesChatResult+"\n\nAsk HERMES is separate from Gemini. Hardware execution remains validated by DJAEGER Agent.",true)
'''
M=M.replace(gemini_box,gemini_box+hermes_ui,1)

# App-to-module chat bridge only. It cannot issue raw hardware/sysfs commands.
repo_anchor='''    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("djaeger-ai gemini-chat-clear",5000); Pair(rc==0,out.trim())\n    }\n'''
assert R.count(repo_anchor)==1
repo_hermes=repo_anchor+'''\n    suspend fun hermesChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){\n        if(prompt.isBlank()) return@withContext Pair(false,"HERMES_CHAT_ERROR=EMPTY_PROMPT")\n        val (rc,out)=suStdin("$module/system/bin/djaeger-hermes-chat chat-stdin",prompt.take(8000),40000)\n        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_ERROR=EMPTY_RESPONSE" else "HERMES_CHAT_FAILED"})\n    }\n\n    suspend fun hermesChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){\n        val (rc,out)=su("$module/system/bin/djaeger-hermes-chat chat-clear",5000)\n        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_HISTORY=CLEARED" else "HERMES_CHAT_CLEAR_FAILED"})\n    }\n'''
R=R.replace(repo_anchor,repo_hermes,1)

# Structural gates: exact order and no accidental Gemini/authority changes.
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('private fun compactModuleVersion',M.index('@Composable fun Overview(s:RuntimeState)'))]
assert ov.count('HermesStatusCard(s)')==1
assert ov.index('StrategyCard(s)') < ov.index('HermesStatusCard(s)') < ov.index('AgentRebuild3Card(s)')
ai=M[M.index('@Composable fun AI(s:RuntimeState)'):M.index('private fun aiSummary',M.index('@Composable fun AI(s:RuntimeState)'))]
assert ai.count('Ask DJAEGER Gemini')==1
assert ai.count('Ask DJAEGER Hermes')==1
assert ai.index('Ask DJAEGER Gemini') < ai.index('GEMINI CONVERSATION') < ai.index('Ask DJAEGER Hermes') < ai.index('HERMES CONVERSATION')
assert 'djaeger-ai gemini-chat-stdin' in R and 'djaeger-ai gemini-chat-clear' in R
assert 'djaeger-hermes-chat chat-stdin' in R
assert '/sys/' not in repo_hermes and '/proc/sys/' not in repo_hermes
assert 'versionCode = 12261' in B
assert 'NEURONGOV3 • ASKHERMES3' in M

main.write_text(M); repo.write_text(R); mapper.write_text(C); reader.write_text(RD); build.write_text(B)
print('REBUILD3_PATCH=PASS')
print('BASELINE=EXACT_PUBLISHED_WORKLOADFINAL1')
print('PAIR=MODULE_129637_CC_12261')
print('HERMES_STATUS_AFTER_STRATEGY=PASS')
print('ASK_HERMES_BELOW_GEMINI=PASS')
print('GEMINI_PATH_PRESERVED=PASS')
print('NEW_RECURRING_ROOT_PROCESS=0')
print('DIRECT_SYSFS_AUTHORITY=NONE')
