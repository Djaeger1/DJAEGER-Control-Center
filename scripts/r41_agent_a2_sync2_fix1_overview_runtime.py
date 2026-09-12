#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
b=root/'app/build.gradle.kts'

# Version = matched module A2 SYNC2 FIX1 / 129615.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12243',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.2-agent-a2-sync2-fix1"',bs,count=1)
b.write_text(bs)

# The mapper already exposes these snapshot sections; RuntimeState previously discarded them.
rs=r.read_text()
old='val bugHealth:BugHealthState=BugHealthState(),val strategy:StrategyTruth=StrategyTruth())'
new='val bugHealth:BugHealthState=BugHealthState(),val strategy:StrategyTruth=StrategyTruth(),val reasoning:String="",val resync:String="",val execution:String="",val policyContext:String="",val attribution:String="")'
assert old in rs, 'SYNC2_RUNTIME_STATE_ANCHOR_MISSING'
rs=rs.replace(old,new,1)
old='''            log=mapped.log,\n            latestDecision=parseDecision(mapped.decisions),'''
new='''            log=mapped.log,\n            reasoning=mapped.reasoning,\n            resync=mapped.resync,\n            execution=mapped.execution,\n            policyContext=mapped.policyContext,\n            attribution=mapped.attribution,\n            latestDecision=parseDecision(mapped.decisions),'''
assert old in rs, 'SYNC2_RUNTIME_CONSTRUCTION_ANCHOR_MISSING'
rs=rs.replace(old,new,1)
r.write_text(rs)

ms=m.read_text()
if 'import androidx.compose.ui.Alignment' not in ms:
    ms=ms.replace('import androidx.compose.ui.Modifier\n','import androidx.compose.ui.Modifier\nimport androidx.compose.ui.Alignment\n',1)

# Replace the complete App shell. Freeform/multiwindow must have its own compact layout.
start=ms.index('@Composable fun App(){')
end=ms.index('private fun thoughtField',start)
app='''@Composable fun App(){
    val repo=remember{DjaegerRepository()}
    val context=androidx.compose.ui.platform.LocalContext.current
    val notifier=remember{BugNotifier(context)}
    var state by remember{mutableStateOf(RuntimeState())}
    var tab by remember{mutableIntStateOf(0)}
    val samples=remember{mutableStateListOf<Sample>()}
    var sampleSessionKey by remember{mutableStateOf("")}
    var manualRefresh by remember{mutableIntStateOf(0)}
    var refreshBusy by remember{mutableStateOf(false)}
    var refreshStatus by remember{mutableStateOf("LOCAL AUTO 1s")}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner){
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){
            while(true){
                val next=repo.snapshot()
                val nextKey="${next.active}|${next.game}|${next.window}|${next.controllerPid}"
                if(sampleSessionKey.isNotBlank()&&nextKey!=sampleSessionKey)samples.clear()
                sampleSessionKey=nextKey
                state=next
                notifier.notifyIfNeeded(state.bugHealth)
                if(next.root&&next.installed&&next.sampleFresh){
                    with(next.telemetry){
                        samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)))
                        while(samples.size>60)samples.removeAt(0)
                    }
                }
                delay(1000)
            }
        }
    }
    LaunchedEffect(manualRefresh){
        if(manualRefresh>0){
            refreshBusy=true
            val before=state.updated
            val fresh=repo.snapshot()
            state=fresh
            notifier.notifyIfNeeded(fresh.bugHealth)
            val now=SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date())
            refreshStatus=if(fresh.error.isNotBlank()) "REFRESH ERROR • $now" else if(fresh.updated>0&&fresh.updated==before) "UNCHANGED • $now" else "UPDATED • $now"
            refreshBusy=false
        }
    }
    MaterialTheme(colorScheme=darkColorScheme(primary=Green,background=Bg,surface=Card)){
        BoxWithConstraints(Modifier.fillMaxSize().background(Bg)){
            val compact=maxWidth<520.dp
            val outerPad=if(compact)10.dp else 16.dp
            Column(Modifier.fillMaxSize().padding(outerPad)){
                if(compact){
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){
                        Column(Modifier.weight(1f)){
                            Text("DJAEGER",fontWeight=FontWeight.Black,style=MaterialTheme.typography.headlineSmall)
                            Text("A2 SYNC2 FIX1 • 1s",color=Muted,style=MaterialTheme.typography.labelSmall)
                        }
                        TextButton(onClick={if(!refreshBusy)manualRefresh++},enabled=!refreshBusy){Text(if(refreshBusy)"…" else "REFRESH")}
                    }
                    Text(refreshStatus,color=Muted,style=MaterialTheme.typography.labelSmall)
                }else{
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){
                        Column(Modifier.weight(1f)){
                            Text("DJAEGER",fontWeight=FontWeight.Black,style=MaterialTheme.typography.headlineMedium,color=MaterialTheme.colorScheme.onBackground)
                            Text("CONTROL CENTER • v0.12.2 A2 SYNC2 FIX1 • REALTIME 1s",color=Muted)
                            Text(refreshStatus,color=Muted,style=MaterialTheme.typography.labelSmall)
                        }
                        Button(onClick={if(!refreshBusy)manualRefresh++},enabled=!refreshBusy){Text(if(refreshBusy)"REFRESHING…" else "REFRESH LOCAL")}
                    }
                }
                Spacer(Modifier.height(if(compact)6.dp else 12.dp))
                val labels=if(compact) listOf("Home","Session","Charts","AI","History","Safety","Bugs","Logs") else listOf("Overview","Session","Charts","AI","History","Safety","Bug & Health","Logs")
                ScrollableTabRow(selectedTabIndex=tab,containerColor=Bg,edgePadding=0.dp){labels.forEachIndexed{i,n->Tab(selected=tab==i,onClick={tab=i},text={Text(n,style=if(compact)MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodyMedium)})}}
                Spacer(Modifier.height(if(compact)6.dp else 12.dp))
                Box(Modifier.fillMaxSize()){
                    when(tab){0->Overview(state);1->Session(state,samples);2->Charts(state,samples);3->AI(state);4->History(state);5->Safety(state);6->BugHealth(state.bugHealth);else->Logs(state)}
                }
            }
        }
    }
}

'''
ms=ms[:start]+app+ms[end:]

# Replace Thought card: derive Gemini from HTTP/THOUGHTS, Agent from BRAIN,
# execution from EXECUTION; never call valid HTTP 200 UNKNOWN merely because BRAIN is empty.
start=ms.index('@Composable fun ThoughtsCard(s:RuntimeState)')
end=ms.index('private fun currentRange',start)
thought='''@Composable fun ThoughtsCard(s:RuntimeState){
    BoxWithConstraints{
        val compact=maxWidth<520.dp
        val now=System.currentTimeMillis()/1000
        val httpCode=envField(s.geminiHttp,"HTTP_CODE")
        val httpAt=envField(s.geminiHttp,"AT").toLongOrNull()?:0L
        val httpAge=if(httpAt>0) now-httpAt else -1L
        val provider=envField(s.geminiHttp,"PROVIDER").ifBlank{"GEMINI"}
        val model=envField(s.geminiHttp,"MODEL")
        val geminiState=when{
            httpCode=="200"&&httpAge in 0..360 -> "ONLINE"
            httpCode=="200"&&httpAge>=0 -> "LAST OK • ${ageLabel(httpAge.toString())}"
            httpCode=="429" -> "RATE LIMIT"
            httpCode=="401"||httpCode=="403" -> "AUTH ERROR"
            httpCode.isNotBlank() -> "HTTP $httpCode"
            else -> "NO HTTP STATE"
        }
        val agentState=envField(s.brain,"AGENT_STATE").ifBlank{if(s.active=="1")"RUNNING" else "IDLE"}
        val agentWinner=envField(s.brain,"AGENT_WINNER").ifBlank{"NONE"}
        val agentReason=envField(s.brain,"AGENT_REASON")
        val execAt=envField(s.execution,"UPDATED_AT").toLongOrNull()?:envField(s.execution,"VERIFY_AT").toLongOrNull()?:0L
        val execFresh=execAt>0&&(now-execAt) in 0..180
        val execStatus=envField(s.execution,"EXECUTION_STATUS").ifBlank{envField(s.execution,"STATE")}.ifBlank{"NONE"}
        val readback=envField(s.execution,"READBACK_MATCH")
        val thoughtSrc=envField(s.thoughts,"SOURCE")
        val thoughtAt=envField(s.thoughts,"AT").toLongOrNull()?:0L
        val thoughtAge=if(thoughtAt>0) now-thoughtAt else -1L
        val thoughtFresh=thoughtAge in 0..360
        val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
        val conf=envField(s.thoughts,"CONFIDENCE")
        val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada reasoning baru yang dipublikasikan."}
        val thoughtTitle=when{
            thoughtSrc=="GEMINI"&&thoughtFresh->"PEMIKIRAN GEMINI"
            thoughtSrc=="GEMINI"->"LAST GEMINI THOUGHT"
            thoughtSrc.contains("HERMES",true)->"PEMIKIRAN HERMES H2"
            else->"PEMIKIRAN DJAEGER"
        }
        val thoughtState=if(thoughtFresh)thoughtStatus else if(thoughtAge>=0)"STALE • ${ageLabel(thoughtAge.toString())}" else thoughtStatus
        val executionLine=if(execFresh) "$execStatus • readback=${if(readback=="1")"VERIFIED" else if(readback.isBlank())"—" else readback}" else if(execAt>0) "LAST $execStatus • ${ageLabel((now-execAt).toString())}" else "NONE"
        val failureLine=if(agentState=="EXECUTION_FAILED"&&agentReason.isNotBlank()) "\nFailure: $agentReason" else ""
        val compactBody="Gemini: $provider • $geminiState\nAgent: $agentState • source=$agentWinner\nExecution: $executionLine$failureLine\n\n$thoughtTitle • $thoughtState\n$text"
        val fullBody="$compactBody\n\nModel: ${model.ifBlank{"—"}}\nThought confidence: ${conf.ifBlank{"—"}}%\nSession: ${if(s.active=="1")"ACTIVE ${s.game} • ${s.window}" else "INACTIVE"}"
        BoxCard("THOUGHT",if(compact)compactBody else fullBody,true)
    }
}

'''
ms=ms[:start]+thought+ms[end:]

# Matched pair markers and visible version.
ms=ms.replace('DUALBRAIN-AGENT-A2-SYNC1','DUALBRAIN-AGENT-A2-SYNC2-FIX1')
ms=ms.replace('AGENT_A2_SYNC1','AGENT_A2_SYNC2_FIX1')
ms=ms.replace('A2 SYNC1 FIX2','A2 SYNC2 FIX1')
m.write_text(ms)

print('R41_RUNTIME_SECTIONS=REASONING_RESYNC_EXECUTION_POLICY_ATTRIBUTION')
print('R41_GEMINI_STATUS=HTTP_PLUS_THOUGHTS')
print('R41_AGENT_STATUS=BRAIN_AGENT_STATE')
print('R41_EXECUTION_STATUS=EXECUTION_SECTION')
print('R41_MULTIWINDOW_LAYOUT=COMPACT_UNDER_520DP')
print('R41_MATCHED_MODULE=129615_SYNC2_FIX1')
