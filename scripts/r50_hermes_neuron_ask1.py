from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

M=main.read_text()
R=repo.read_text()
B=build.read_text()

# 1) Compact HERMES status card. It reads only already-published brain state.
#    It has no network or hardware authority.
anchor='@Composable fun HermesCloudCard(s:RuntimeState){'
if anchor not in M:
    raise SystemExit('R50_FAIL: HermesCloudCard anchor missing')
card=r'''@Composable fun HermesStatusCard(s:RuntimeState){
    val cloudState=envField(s.brain,"HERMES_CLOUD_STATE").ifBlank{"NOT_YET_USED"}
    val cloudAuth=envField(s.brain,"HERMES_CLOUD_AUTH").ifBlank{"UNKNOWN"}
    val cloudRoute=envField(s.brain,"HERMES_CLOUD_ROUTE").uppercase()
    val route=if(cloudRoute=="FAST"||cloudRoute=="SMART"||cloudRoute=="DEEP") cloudRoute else "LOCAL"
    val cloud=when{
        cloudState=="READY"&&route!="LOCAL"->"ACTIVE"
        cloudState=="READY"->"READY"
        cloudState=="BUDGET_RESERVE"->"READY"
        cloudState=="NOT_YET_USED"&&cloudAuth=="CONFIGURED"->"READY"
        cloudState=="QUOTA_EXHAUSTED"||cloudState=="FAILED"||cloudState=="UNAVAILABLE"->"OFFLINE"
        else->if(cloudAuth=="CONFIGURED") "READY" else "OFFLINE"
    }
    val used=envField(s.brain,"HERMES_NEURON_USED_EST").ifBlank{"0"}
    val limit=envField(s.brain,"HERMES_NEURON_LIMIT").ifBlank{"10000"}
    val tier=envField(s.brain,"HERMES_NEURON_TIER").ifBlank{"NORMAL"}
    BoxCard("HERMES: ${if(s.installed) "ONLINE" else "OFFLINE"}","Route    $route\nCloud    $cloud\nNeurons  $used / $limit • EST",true)
}

'''
M=M.replace(anchor,card+anchor,1)

# 2) Preserve the established Overview order. Add exactly one card directly after STRATEGI.
overview_old='NetworkCard(s.network);StrategyCard(s);AgentRebuild3Card(s)'
overview_new='NetworkCard(s.network);StrategyCard(s);HermesStatusCard(s);AgentRebuild3Card(s)'
if M.count(overview_old)!=1:
    raise SystemExit(f'R50_FAIL: overview anchor count={M.count(overview_old)}')
M=M.replace(overview_old,overview_new,1)

# 3) Add independent HERMES chat state beside, not inside, Gemini state.
state_old='var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}'
state_new=state_old+'\n    var hermesChatInput by remember{mutableStateOf("")}; var hermesChatResult by remember{mutableStateOf("Ask HERMES naturally. ONE HERMES will choose LOCAL / FAST / SMART / DEEP automatically.")}'
if M.count(state_old)!=1:
    raise SystemExit('R50_FAIL: AI chat state anchor missing')
M=M.replace(state_old,state_new,1)

# 4) Bridge operations. Gemini path is untouched.
clear_old='"CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}'
clear_new=clear_old+'\n            "HERMES_CHAT"->{val r=repo.hermesChat(hermesChatInput);hermesChatResult=r.second.ifBlank{"HERMES_CHAT_ERROR=EMPTY_RESPONSE"}}\n            "HERMES_CLEAR_CHAT"->{val r=repo.hermesChatClear();hermesChatResult=r.second.ifBlank{"HERMES_CHAT_HISTORY=CLEARED"}}'
if M.count(clear_old)!=1:
    raise SystemExit('R50_FAIL: Gemini clear-chat bridge anchor missing')
M=M.replace(clear_old,clear_new,1)

# 5) Ask HERMES section is immediately below the existing Gemini conversation.
gemini_conversation='BoxCard("GEMINI CONVERSATION",chatResult+"\\n\\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)'
hermes_ui=r'''BoxCard("GEMINI CONVERSATION",chatResult+"\n\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)
        OutlinedTextField(value=hermesChatInput,onValueChange={hermesChatInput=it.take(8000)},label={Text("Ask DJAEGER Hermes")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="HERMES_CHAT"},enabled=bridgeOp==null&&hermesChatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK HERMES")}
            Button(onClick={bridgeOp="HERMES_CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW HERMES CHAT")}
        }
        BoxCard("HERMES CONVERSATION",hermesChatResult+"\n\nONE HERMES chooses LOCAL / FAST / SMART / DEEP. Cloud failure or exhausted quota falls back to HERMES LOCAL; Gemini chat is separate.",true)'''
if M.count(gemini_conversation)!=1:
    raise SystemExit(f'R50_FAIL: Gemini conversation anchor count={M.count(gemini_conversation)}')
M=M.replace(gemini_conversation,hermes_ui,1)

# 6) Repository methods call the module helper. No app-direct network and no sysfs writes.
repo_anchor='''    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-chat-clear",5000); Pair(rc==0,out.trim())
    }
'''
repo_insert=repo_anchor+'''\n    suspend fun hermesChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(prompt.isBlank()) return@withContext Pair(false,"HERMES_CHAT_ERROR=EMPTY_PROMPT")
        val (rc,out)=suStdin("$module/system/bin/djaeger-hermes-cloud chat-stdin",prompt.take(8000),40000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_ERROR=EMPTY_RESPONSE" else "HERMES_CHAT_FAILED"})
    }

    suspend fun hermesChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/system/bin/djaeger-hermes-cloud chat-clear",5000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_HISTORY=CLEARED" else "HERMES_CHAT_CLEAR_FAILED"})
    }
'''
if R.count(repo_anchor)!=1:
    raise SystemExit('R50_FAIL: repository Gemini clear anchor missing')
R=R.replace(repo_anchor,repo_insert,1)

# Version name only: preserve versionCode/module pairing contract.
if 'hermescloud1-workloadfinal1' in B and 'neurongov1-askhermes1' not in B:
    B=B.replace('hermescloud1-workloadfinal1','hermescloud1-workloadfinal1-neurongov1-askhermes1')

# Shadow-time assertions before anything is written.
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('private fun compactModuleVersion',M.index('@Composable fun Overview(s:RuntimeState)'))]
assert ov.index('StrategyCard(s)') < ov.index('HermesStatusCard(s)') < ov.index('AgentRebuild3Card(s)')
assert ov.count('HermesStatusCard(s)')==1
ai=M[M.index('@Composable fun AI(s:RuntimeState)'):M.index('private fun aiSummary',M.index('@Composable fun AI(s:RuntimeState)'))]
assert ai.index('Ask DJAEGER Gemini') < ai.index('Ask DJAEGER Hermes')
assert ai.count('Ask DJAEGER Gemini')==1
assert ai.count('Ask DJAEGER Hermes')==1
assert 'hermesChat(hermesChatInput)' in ai
assert 'djaeger-hermes-cloud chat-stdin' in R
assert '/sys/' not in R

main.write_text(M)
repo.write_text(R)
build.write_text(B)
print('R50_HERMES_NEURON_ASK1=PASS')
print('OVERVIEW_STRATEGY_THEN_HERMES_STATUS=PASS')
print('ASK_GEMINI_THEN_ASK_HERMES=PASS')
print('APP_DIRECT_NETWORK_FOR_HERMES=NONE')
print('APP_DIRECT_SYSFS_FOR_HERMES=NONE')
