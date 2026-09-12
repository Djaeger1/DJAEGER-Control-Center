package com.djaeger.controlcenter
import kotlinx.coroutines.launch

import android.os.Bundle
import android.Manifest
import android.os.Build
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity:ComponentActivity(){override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);setContent{App()}}}
private val Bg=Color(0xFF090B10); private val Card=Color(0xFF121722); private val Green=Color(0xFF43E38A); private val Muted=Color(0xFF98A2B3); private val Amber=Color(0xFFFFC857); private val Red=Color(0xFFFF6B6B)

data class Sample(val fps:Double,val frame:Double,val cpu:Float,val gpu:Float,val skin:Float,val bat:Float)

private fun sampleTemp(value:Int)=if(value>=0)value.toFloat() else Float.NaN
private fun tempText(value:Int)=if(value>=0)"$value°C" else "—"
private fun positiveText(value:Double,suffix:String)=if(value>0)"%.1f%s".format(value,suffix) else "—"
private fun jankText(value:Double)=if(value.isFinite()&&value>=0.0)"%.1f%%".format(value) else "—"
private fun runtimeStateStale(s:RuntimeState):Boolean{
    val ttl=if(s.active=="1")5L else 15L
    val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl
    return if(s.active=="1") !s.sampleFresh else runtimeStale
}
private fun positiveLongText(value:Long,divisor:Long,suffix:String)=if(value>0)"${value/divisor}$suffix" else "—"
private fun stat3(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f / %.1f%s".format(values.average(),values.minOrNull()?:0.0,values.maxOrNull()?:0.0,unit)
private fun stat2(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f%s".format(values.average(),values.maxOrNull()?:0.0,unit)

@Composable fun App(){
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

private fun thoughtField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\'') ?: ""
private fun envField(raw:String,key:String):String = thoughtField(raw,key)
private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI"
    "HERMES_LOCAL","HERMES_H2"->"HERMES H2"
    "AI_AGENT_A2","AGENT_A2"->"AI AGENT A2"
    else->raw.ifBlank{"—"}
}
private fun ageLabel(raw:String):String{
    val n=raw.toLongOrNull()?:return "—"
    if(n<0)return "—"
    return when{n<60->"${n}s";n<3600->"${n/60}m ${n%60}s";else->"${n/3600}h ${(n%3600)/60}m"}
}

@Composable fun ThoughtsCard(s:RuntimeState){
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

private fun currentRange(raw:String,unit:String):String{
    val v=raw.trim()
    return if(v.isBlank()||v.contains("NA")) "—" else "$v $unit"
}

private fun planRange(a:String,b:String,unit:String):String{
    val x=a.trim(); val y=b.trim()
    return if(x.isBlank()||y.isBlank()||x.equals("NA",true)||y.equals("NA",true)) "—" else "$x-$y $unit"
}

@Composable fun HermesCard(s:RuntimeState){
    val hState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"UNAVAILABLE"}}
    val hProfile=envField(s.brain,"HERMES_PROFILE").ifBlank{"—"}
    val hConfidence=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val hMode=envField(s.brain,"HERMES_MODE").ifBlank{"PROFILE"}
    val hVariable=envField(s.brain,"HERMES_VARIABLE").ifBlank{"NA"}
    val hValue=envField(s.brain,"HERMES_VARIABLE_VALUE").ifBlank{"0"}
    val hVariableState=envField(s.brain,"HERMES_VARIABLE_STATE").ifBlank{"NONE"}
    val hSamples=envField(s.brain,"HERMES_VARIABLE_SAMPLES").ifBlank{"0"}
    val hRate=envField(s.brain,"HERMES_VARIABLE_SUCCESS_RATE").ifBlank{"0"}
    val hScope=envField(s.brain,"HERMES_EVIDENCE_SCOPE").ifBlank{"—"}
    val hFilter=envField(s.brain,"HERMES_EVIDENCE_FILTER").ifBlank{"—"}
    val hReason=envField(s.brain,"HERMES_REASON").ifBlank{"Belum ada reasoning Hermes yang dipublikasikan module."}
    val currentBrain=envField(s.brain,"CURRENT_BRAIN")
    val finalSource=envField(s.brain,"FINAL_SOURCE")
    val agentWinner=envField(s.brain,"AGENT_WINNER").ifBlank{"NONE"}
    val displayState=when(hState){
        "VALID"->if(agentWinner=="HERMES") "SELECTED BY AGENT" else "READY"
        "LOW_CONFIDENCE"->"LEARNING • LOW CONFIDENCE"
        "UNAVAILABLE"->"UNAVAILABLE"
        else->hState
    }
    val authority="REASONING ONLY • AI AGENT A2 OWNS DECISION + EXECUTION"
    val body="State: $displayState\nMode: $hMode\nProfile: $hProfile\nConfidence: $hConfidence%\nVariable: $hVariable\nValue: $hValue\nVariable state: $hVariableState\nContext samples: $hSamples\nContext success rate: $hRate%\nEvidence scope: $hScope\nEvidence filter: $hFilter\nBrain source: ${currentBrain.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nAuthority: $authority\nReason: $hReason"
    BoxCard("HERMES H2 • LOCAL BRAIN",body,true)
}

@Composable fun HumanComfortHcc1Card(s:RuntimeState){
    val body=s.hermesHumanComfort.trim().ifBlank{"UNAVAILABLE — HCC1 human comfort state not published by module."}
    BoxCard("HERMES • HUMAN COMFORT HCC1",body,true)
}

@Composable fun ContextVNextCard(s:RuntimeState){
    fun ctx(raw:String,missing:String)=raw.trim().ifBlank{missing}
    val status=ctx(s.hermesCtx1Status,"UNAVAILABLE — CTX1 status not published.")
    val runtime=ctx(s.hermesCtx1Runtime,"UNAVAILABLE — CTX1 runtime context not published.")
    val safety=ctx(s.hermesCtx1Safety,"UNAVAILABLE — CTX1 safety context not published.")
    val hardware=ctx(s.hermesCtx1Hardware,"UNAVAILABLE — CTX1 hardware context not published.")
    val memory=ctx(s.hermesCtx1Memory,"UNAVAILABLE — CTX1 memory context not published.")
    val learning=ctx(s.hermesCtx1Learning,"UNAVAILABLE — CTX1 learning context not published.")
    val body="STATUS\n$status\n\nRUNTIME\n$runtime\n\nSAFETY\n$safety\n\nHARDWARE\n$hardware\n\nMEMORY\n$memory\n\nLEARNING\n$learning"
    BoxCard("HERMES CTX1 • CONTEXT VNEXT • SHADOW",body,true)
}

@Composable fun MemoryVNextCard(s:RuntimeState){
    val status=s.hermesCognitionStatus.trim().ifBlank{"STATE=UNAVAILABLE"}
    val body=s.hermesMemoryVNext.trim().ifBlank{"STATE=UNAVAILABLE — Memory vNext has not published yet."}
    BoxCard("HERMES • MEMORY VNEXT",status+"\n\n"+body,true)
}

@Composable fun ReasoningV2Card(s:RuntimeState){
    val body=s.hermesReasoningV2.trim().ifBlank{"STATE=UNAVAILABLE — Reasoning v2 has not published yet."}
    BoxCard("HERMES • REASONING V2",body,true)
}

@Composable fun SkillsVNextCard(s:RuntimeState){
    val body=s.hermesSkillsVNext.trim().ifBlank{"STATE=UNAVAILABLE — Skills vNext has not published yet."}
    BoxCard("HERMES • SKILLS VNEXT",body,true)
}

@Composable fun LearningResearchV2Card(s:RuntimeState){
    val learning=s.hermesLearningV2.trim().ifBlank{"STATE=UNAVAILABLE — Learning v2 has not published yet."}
    val research=s.hermesResearchV2.trim().ifBlank{"STATE=UNAVAILABLE — Research v2 has not published yet."}
    BoxCard("HERMES • LEARNING + RESEARCH V2","LEARNING\n$learning\n\nRESEARCH\n$research",true)
}

@Composable fun StrategyCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val brainProfile=envField(s.brain,"BRAIN_PROFILE").ifBlank{envField(s.brain,"FINAL_PROFILE")}
    val finalProfile=envField(s.brain,"FINAL_PROFILE").ifBlank{s.telemetry.profile}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val adjustment=envField(s.brain,"FINAL_ADJUSTMENT").ifBlank{"NONE"}
    val execMode=envField(s.brain,"EXEC_MODE").ifBlank{"PROFILE"}
    val little=envField(s.brain,"EXEC_LITTLE")
    val big=envField(s.brain,"EXEC_BIG")
    val gpu=envField(s.brain,"EXEC_GPU")
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{"0"}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{"—"}
    val hermesState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"—"}}
    val hermesConf=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val validation=if(srValidation.isNotBlank()) "$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}" else "AGENT A2 INTERNAL VERIFICATION / FAIL-CLOSED"
    val body="Gemini: $cloudConnection\nTruth: CURRENT BRAIN / FUSED\nCloud proposal: $cloudState • ${cloudScore}%\nCloud reason: $cloudReason\nHermes proposal: $hermesState • ${hermesConf}%\nCurrent brain: ${brainLabel(currentBrain)}\nBrain decision: ${brainMode.ifBlank{"—"}}\nBrain profile: ${brainProfile.ifBlank{"—"}}\nFinal profile / mode: $finalProfile / $execMode\nFinal source: ${finalSource.ifBlank{"—"}}\nFinal adjustment: $adjustment\nUser mode: ${s.userMode}\nCPU little: ${currentRange(little,"kHz")}\nCPU big: ${currentRange(big,"kHz")}\nGPU: ${currentRange(gpu,"MHz")}\nVerifikasi Agent: $validation"
    BoxCard("STRATEGI",body,true)
}

@Composable fun Overview(s:RuntimeState){val power=if(s.telemetry.powerMw>=0)"%.1f mW".format(s.telemetry.powerMw) else "—";val current=if(s.telemetry.currentUa>0)"${s.telemetry.currentUa} µA" else "—";val voltage=if(s.telemetry.voltageUv>0)"${s.telemetry.voltageUv} µV" else "—";Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);MatchedPairSyncCard(s);ThoughtsCard(s);AgentA2Card(s);HermesCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS",positiveText(s.telemetry.fps,""),Modifier.weight(1f));Metric("Frame",positiveText(s.telemetry.frameMs," ms"),Modifier.weight(1f));Metric("Jank",jankText(s.telemetry.jank),Modifier.weight(1f))};ThermalRow(s);NetworkCard(s.network);HumanComfortHcc1Card(s);ContextVNextCard(s);MemoryVNextCard(s);ReasoningV2Card(s);SkillsVNextCard(s);LearningResearchV2Card(s);StrategyCard(s);OutcomeLearningCard(s);StrategyCompositionCard(s);DecisionPipelineCard(s);BoxCard("PERFORMANCE","Little: ${positiveLongText(s.telemetry.littleKhz,1000," MHz")}\nBig: ${positiveLongText(s.telemetry.bigKhz,1000," MHz")}\nGPU: ${positiveLongText(s.telemetry.gpuHz,1_000_000," MHz")}\nProfile: ${s.telemetry.profile}\nP95/P99: ${positiveText(s.telemetry.p95," ms")} / ${positiveText(s.telemetry.p99," ms")}");BoxCard("POWER","${s.telemetry.batteryStatus} • $power\n$current • $voltage\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}}
@Composable fun StatusCard(s:RuntimeState){val stale=runtimeStateStale(s);val session=when{ s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"};BoxCard("ENGINE / SESSION",if(s.installed)"${if(s.active=="1")"● ACTIVE" else "○ IDLE"} • ${if(stale)"STALE" else "LIVE"}\nModule: ${s.moduleVersion}\nGame: ${s.game}\nWindow: ${s.window}\nProfile: ${s.telemetry.profile}\nLast sample: $session\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")}
@Composable fun NetworkCard(n:NetworkState){
    val clipboard=LocalClipboardManager.current
    val body="Ping ${n.ping} ms • Avg ${n.avg} ms • P95 ${n.p95} ms • Jitter ${n.jitter} ms • Loss ${n.loss}% • Quality ${n.quality}"
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("NETWORK",color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString(body))}){Text("COPY",maxLines=1)}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){NetworkMetric("Ping",if(n.fresh) "${n.ping} ms" else "—");NetworkMetric("Avg",if(n.fresh) "${n.avg} ms" else "—");NetworkMetric("P95",if(n.fresh) "${n.p95} ms" else "—");NetworkMetric("Jitter",if(n.fresh) "${n.jitter} ms" else "—");NetworkMetric("Loss",if(n.fresh) "${n.loss}%" else "—")}
        Spacer(Modifier.height(8.dp));Text("Quality: ${if(n.fresh)n.quality else "INACTIVE"}",color=if(n.fresh) Green else Muted,fontWeight=FontWeight.Bold)
    }}
}
@Composable fun NetworkMetric(label:String,value:String){Column{Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(value,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.bodyMedium)}}


@Composable fun StrategyCompositionCard(s:RuntimeState){val x=s.strategy;BoxCard("STRATEGY COMPOSITION • LAST PROMOTED PLAN",(if(runtimeStateStale(s)) "STALE SNAPSHOT — NOT CURRENT RUNTIME\n" else "")+"Source: ${x.source}\nMode: ${s.userMode}\nCPU LITTLE: ${x.cpuLittleMin} → ${x.cpuLittleMax}\nCPU BIG: ${x.cpuBigMin} → ${x.cpuBigMax}\nGPU: ${x.gpuMin} → ${x.gpuMax}\nCPU governor: ${x.cpuGovernor} • GPU governor: ${x.gpuGovernor}\nPower/bias: ${x.powerBias} • Burst/lease: ${x.burstLease}\nComfort ceiling: ${x.comfortCeiling} • Confidence: ${x.confidence}\nRationale: ${x.rationale}",true)}
@Composable fun DecisionPipelineCard(s:RuntimeState){val x=s.strategy;BoxCard("DECISION PIPELINE","PROPOSED: ${x.proposal}\nVALIDATED / REJECTED: ${x.validation}\nAPPLIED: ${x.applied}\nREADBACK VERIFIED: ${x.readback}\nOUTCOME: ${x.outcome}\nDecision source: ${x.source}",true)}
@Composable fun OutcomeLearningCard(s:RuntimeState){val x=s.strategy;BoxCard("OUTCOME + LEARNING","FPS: ${x.fpsOutcome} • Frame: ${x.frameOutcome}\nThermal: ${x.thermalOutcome} • Power: ${x.powerOutcome}\nLearning samples: ${x.learningSamples}\nLearning confidence: ${x.learningConfidence}\nPromotion: ${x.learningPromotion}\nOnly module-published truth is displayed; missing fields remain unavailable.",true)}

@Composable fun ThermalRow(s:RuntimeState){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Thermal("CPU",s.telemetry.cpuT,Modifier.weight(1f));Thermal("GPU",s.telemetry.gpuT,Modifier.weight(1f));Thermal("Skin",s.telemetry.skinT,Modifier.weight(1f));Thermal("Battery",s.telemetry.batT,Modifier.weight(1f))}}
@Composable fun Thermal(label:String,t:Int,m:Modifier){val c=when{t<0->Muted;t>=50->Red;t>=43->Amber;else->Green};Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(tempText(t),color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}



@Composable fun BugHealth(b:BugHealthState){
    val clipboard=LocalClipboardManager.current
    val status=if(b.openBug) "OPEN" else b.health.ifBlank{"UNKNOWN"}
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("BUG & HEALTH","Status: $status\nSeverity: ${b.severity}\nComponent: ${b.component.ifBlank{"—"}}\nCode: ${b.code.ifBlank{"—"}}\nEvent ID: ${b.eventId.ifBlank{"—"}}")
        BoxCard("OBSERVED FACTS",b.facts.ifBlank{b.summary.ifBlank{"No official DJAEGER bug facts published."}},true)
        BoxCard("CAUSE HYPOTHESIS",b.hypothesis.ifBlank{"No hypothesis published. Hypotheses are explanatory only and are not the source of bug truth."},true)
        BoxCard("ACTION / RECOVERY","Action: ${b.action.ifBlank{"—"}}\nRecovery: ${b.recovery.ifBlank{"—"}}\nDecision ID: ${b.decisionId.ifBlank{"—"}}\nTransaction ID: ${b.transactionId.ifBlank{"—"}}")
        BoxCard("RECENT BUG EVENTS",b.recentEvents.ifBlank{"No bug events recorded."},true)
        Button(onClick={clipboard.setText(AnnotatedString(BugHealthParser.diagnosticReport(b)))},modifier=Modifier.fillMaxWidth()){Text("COPY DIAGNOSTIC REPORT")}
    }
}

@Composable fun Session(s:RuntimeState,samples:List<Sample>){
    val fps=samples.map{it.fps}.filter{it.isFinite()&&it>0};val frame=samples.map{it.frame}.filter{it.isFinite()&&it>0};val cpu=samples.map{it.cpu.toDouble()}.filter{it.isFinite()&&it>=0};val gpu=samples.map{it.gpu.toDouble()}.filter{it.isFinite()&&it>=0};val skin=samples.map{it.skin.toDouble()}.filter{it.isFinite()&&it>=0}
    val phase=monitorPhase(s)
    val anomalies=anomalySummary(s,samples)
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("MONITOR SESSION","Samples: ${samples.size} / 60\nWindow: ${s.window} • Game: ${s.game}\nObserved phase: $phase\nThis phase is a monitor-side interpretation, not a command to DJAEGER.")
        BoxCard("60-SECOND STATISTICS","FPS avg/min/max: ${stat3(fps,"")}\nFrame avg/peak: ${stat2(frame," ms")}\nCPU avg/peak: ${stat2(cpu,"°C")}\nGPU avg/peak: ${stat2(gpu,"°C")}\nSkin avg/peak: ${stat2(skin,"°C")}")
        BoxCard("ANOMALY WATCH",anomalies)
        BoxCard("CURRENT INTERPRETATION",humanDecision(s))
    }
}
private fun monitorPhase(s:RuntimeState):String{
    val text=(s.brain+" "+s.envelope+" "+s.latestDecision?.outcome.orEmpty()).lowercase()
    return when{
        s.active!="1"||s.window.equals("INACTIVE",true)->"IDLE / RESTORED WINDOW"
        "recover" in text||"cool" in text->"RECOVERY / THERMAL RELIEF"
        "thermal" in text||s.telemetry.skinT>=45||s.telemetry.cpuT>=55->"THERMAL INTERVENTION LIKELY"
        "boost" in text||"ramp" in text->"PERFORMANCE RAMP / BOOST LIKELY"
        else->"HOLD / ADAPTIVE CONTROL"
    }
}
private fun anomalySummary(s:RuntimeState,samples:List<Sample>):String{
    val a=mutableListOf<String>(); val now=System.currentTimeMillis()/1000
    if(!s.root)a.add("Root unavailable")
    if(!s.installed)a.add("DJAEGER module not found")
    if(runtimeStateStale(s))a.add(if(s.updated>0)"Runtime status stale (${now-s.updated}s)" else "Runtime status stale / not reported")
    if(s.active=="1"&&s.controllerPid.isBlank())a.add("Active session without reported controller PID")
    if(s.telemetry.powerValid.equals("0")||s.telemetry.powerValid.equals("false",true))a.add("Battery power telemetry invalid: ${s.telemetry.powerReason}")
    if(s.telemetry.skinT>=48)a.add("High skin temperature: ${s.telemetry.skinT}°C")
    if(s.telemetry.cpuT>=60)a.add("High CPU temperature: ${s.telemetry.cpuT}°C")
    if(samples.size>=10){val recent=samples.takeLast(10); val avg=recent.map{it.fps}.average(); if(avg>0&&recent.last().fps<avg*0.70)a.add("FPS dropped >30% versus recent 10s average") }
    return if(a.isEmpty())"No monitor-side anomaly detected in the current snapshot." else a.joinToString("\n") { "• $it" }
}
private fun humanDecision(s:RuntimeState):String{
    val d=s.latestDecision; val p=s.latestPlan
    if(d==null&&p==null)return "No structured decision/plan is available yet. Raw DJAEGER state remains visible in AI and History."
    val outcome=d?.outcome?.ifBlank{"not reported"}?:"not reported"
    return "DJAEGER is publishing profile ${d?.profile?:p?.profile?:s.telemetry.profile}. Latest recorded outcome: $outcome. Current monitor interpretation: ${monitorPhase(s)}. Thermal and restoration authority remain inside DJAEGER; this screen only explains published state."
}

@Composable fun Charts(s:RuntimeState,samples:List<Sample>){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){BoxCard("LIVE WINDOW","Last ${samples.size} seconds • refresh 1s\nMissing sensors stay as gaps and render as —.");LineChartCard("FPS",samples.map{it.fps.toFloat()},0f,120f,positiveText(s.telemetry.fps,""));LineChartCard("FRAME TIME",samples.map{it.frame.toFloat()},0f,50f,positiveText(s.telemetry.frameMs," ms"));LineChartCard("CPU TEMPERATURE",samples.map{it.cpu},20f,70f,tempText(s.telemetry.cpuT));LineChartCard("GPU TEMPERATURE",samples.map{it.gpu},20f,70f,tempText(s.telemetry.gpuT));LineChartCard("SKIN TEMPERATURE",samples.map{it.skin},20f,55f,tempText(s.telemetry.skinT))}}
@Composable fun LineChartCard(title:String,values:List<Float>,min:Float,max:Float,current:String){
    val clipboard=LocalClipboardManager.current
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString("["+title+"] "+current))}){Text("COPY",maxLines=1)}}
        Text(current,fontWeight=FontWeight.Bold);Spacer(Modifier.height(10.dp))
        Canvas(Modifier.fillMaxWidth().height(120.dp)){if(values.size>1){val lo=min;val hi=max.coerceAtLeast(lo+1f);val step=size.width/(values.size-1);for(i in 1 until values.size){val a=values[i-1];val b=values[i];if(a.isFinite()&&b.isFinite()){val y1=size.height-(a.coerceIn(lo,hi)-lo)/(hi-lo)*size.height;val y2=size.height-(b.coerceIn(lo,hi)-lo)/(hi-lo)*size.height;drawLine(color=Green,start=Offset((i-1)*step,y1),end=Offset(i*step,y2),strokeWidth=3f)}}}}
    }}
}

@Composable fun AI(s:RuntimeState){
    val repo=remember{DjaegerRepository()};val uiScope=rememberCoroutineScope(); var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}
    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}
    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}
    var authorityStatus by remember{mutableStateOf("Authority sync not loaded yet.")}
    var kernelStatus by remember{mutableStateOf("Kernel capability not loaded yet.")}
    var auditStatus by remember{mutableStateOf("Maturity audit not run yet.")}
    var recoveryStatus by remember{mutableStateOf("Recovery state not loaded yet.")}
    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}
    var comfortCommandStatus by remember{mutableStateOf("HCC1 controls ready. Current truth is read from cc_snapshot.")}
    LaunchedEffect(request){val q=request;if(q!=null){val r=repo.setUserMode(q);result=r.second;request=null}}
    LaunchedEffect(bridgeOp){
        when(bridgeOp){
            "STATUS"->{val r=repo.geminiKeyStatus();bridgeStatus=r.second.ifBlank{"KEY_CONFIGURED=NO"}}
            "SAVE"->{val r=repo.saveGeminiKey(keyInput);bridgeStatus=r.second;if(r.first)keyInput=""}
            "DELETE"->{val r=repo.deleteGeminiKey();bridgeStatus=r.second}
            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}
            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}
            "AUTHORITY"->{val r=repo.authoritySyncStatus();authorityStatus=r.second.ifBlank{"AUTHORITY_SYNC=EMPTY"}}
            "KERNEL"->{val r=repo.kernelCapabilitySummary();kernelStatus=r.second.ifBlank{"KERNEL_CAPABILITY=EMPTY"}}
            "AUDIT"->{val r=repo.maturityAudit();auditStatus=r.second.ifBlank{"MATURITY_AUDIT=EMPTY"}}
            "RECOVERY"->{val r=repo.recoveryStatus();recoveryStatus=r.second.ifBlank{"RECOVERY_STATUS=EMPTY"}}
            "SNAPSHOT"->{val r=repo.snapshotLifecycleStatus();snapshotStatus=r.second.ifBlank{"SNAPSHOT_STATUS=EMPTY"}}
            "COMFORT_COOL"->{val r=repo.setHumanComfortPreset("COOL_STABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}
            "COMFORT_BASELINE"->{val r=repo.setHumanComfortPreset("BASELINE");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}
            "COMFORT_RESET"->{val r=repo.setHumanComfortPreset("RESET");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}
            "FEEDBACK_VERY_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("VERY_COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}
            "FEEDBACK_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}
            "FEEDBACK_LESS_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("LESS_COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}
            "FEEDBACK_UNCOMFORTABLE"->{val r=repo.submitHumanComfortFeedback("UNCOMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}
        }
        bridgeOp=null
    }
    val supported=s.moduleVersion.contains("DUALBRAIN-AGENT-A2-SYNC2-FIX1"); val retained=humanDecision(s); val brainText=if(s.brain.isBlank()) "No Hermes H2 state published.\nLAST SESSION:\n"+retained else s.brain
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)
        BoxCard("SESSION SAFETY",(s.sessionSafety+"\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)
        BoxCard("GAMING TURBO MODE","Module: ${s.moduleVersion}\nConfirmed active mode: ${s.userMode}\nContract: ${if(supported) "DIRECT USER MODES READY" else "REQUIRES A2 SYNC1 MATCHED MODULE"}\n${if(result.isBlank()) "Select a mode below." else "Last command: $result"}",true)
        if(supported){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach{mode->Button(onClick={request=mode},enabled=request==null,contentPadding=PaddingValues(horizontal=7.dp,vertical=5.dp),modifier=Modifier.weight(1f)){Text(mode,style=MaterialTheme.typography.labelSmall)}}}}
        BoxCard("MODE AUTHORITY","Mode changes use only the trusted djaeger-ai mode interface. Native thermal protection remains independent and authoritative.",true)
        BoxCard("HUMAN COMFORT HCC1 CONTROL",s.hermesHumanComfort.trim().ifBlank{"HCC1 state waiting for module publication."}+"\n\nLast command: $comfortCommandStatus",true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="COMFORT_COOL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("COOL STABLE",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="COMFORT_BASELINE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("BASELINE",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="COMFORT_RESET"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RESET",style=MaterialTheme.typography.labelSmall)}
        }
        Text("FEEDBACK KENYAMANAN • menjadi evidence personal HCC1",color=Muted,style=MaterialTheme.typography.labelMedium)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            OutlinedButton(onClick={bridgeOp="FEEDBACK_VERY_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SANGAT NYAMAN",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="FEEDBACK_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NYAMAN",style=MaterialTheme.typography.labelSmall)}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            OutlinedButton(onClick={bridgeOp="FEEDBACK_LESS_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KURANG NYAMAN",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="FEEDBACK_UNCOMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("TIDAK NYAMAN",style=MaterialTheme.typography.labelSmall)}
        }
        MatchedPairSyncCard(s)
        
        
        
        
        
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="AUTHORITY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SYNC")}
            Button(onClick={bridgeOp="KERNEL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KERNEL")}
            Button(onClick={bridgeOp="AUDIT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("AUDIT")}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="RECOVERY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RECOVERY")}
            Button(onClick={bridgeOp="SNAPSHOT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SNAPSHOT")}
        }
        BoxCard("DIAGNOSTIC COMMAND RESULTS","AUTHORITY SYNC\n$authorityStatus\n\nKERNEL CAPABILITY\n$kernelStatus\n\nMATURITY AUDIT\n$auditStatus\n\nSESSION RECOVERY\n$recoveryStatus\n\nSNAPSHOT LIFECYCLE\n$snapshotStatus",true)
        BoxCard("GEMINI KEY STATUS • CACHED LOCAL RECORD",bridgeStatus,true)
        val vaultContext=androidx.compose.ui.platform.LocalContext.current
        val vault4=remember(vaultContext){KeyVault4(vaultContext)}
        var vaultSlot by remember{mutableStateOf(1)}
        var vaultEpoch by remember{mutableStateOf(0)}
        var moduleVaultStatus by remember { mutableStateOf("") }
        LaunchedEffect(vaultEpoch) { val (_,runtimeVault)=repo.geminiKeyVaultStatus(); moduleVaultStatus=runtimeVault }
        val vaultStatus4 = moduleVaultStatus.ifBlank { vault4.status()+"\nLOCAL STAGING ONLY • runtime vault status unavailable" }
        BoxCard("GEMINI KEY VAULT • 4 MANUAL SLOTS",vaultStatus4+"\nActive: KEY $vaultSlot\nAUTO ROTATION: HTTP 429 → next READY key • cooldown/backoff • all limited → Hermes H2 fallback.",true)
                Button(onClick={ val entries=(1..4).mapNotNull{slot->vault4.get(slot)?.let{k->slot to k}}; val keys=entries.map{it.second}; val preferred=(entries.indexOfFirst{it.first==vault4.active()}+1).let{if(it>0)it else 1}; uiScope.launch { repo.syncGeminiKeyPool(keys,preferred); vaultEpoch++ } }, enabled=vault4.configuredKeys().isNotEmpty()){ Text("SYNC 4-KEY POOL") }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){(1..4).forEach{n->OutlinedButton(onClick={vaultSlot=n},modifier=Modifier.weight(1f)){Text("KEY $n")}}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={ if(keyInput.isNotBlank()){ vault4.put(vaultSlot,keyInput); keyInput=""; vaultEpoch++ } },enabled=keyInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE SLOT")}
            Button(onClick={ val k=vault4.get(vaultSlot); if(k!=null){ vault4.setActive(vaultSlot); keyInput=k; bridgeOp="SAVE"; vaultEpoch++ } },modifier=Modifier.weight(1f)){Text("SELECT")}
            Button(onClick={ vault4.delete(vaultSlot); vaultEpoch++ },modifier=Modifier.weight(1f)){Text("DELETE SLOT")}
        }
        Text("TELEMETRI 1 DETIK • LITTLE ${if(s.telemetry.littleKhz>=0)s.telemetry.littleKhz/1000 else 0} MHz • BIG ${if(s.telemetry.bigKhz>=0)s.telemetry.bigKhz/1000 else 0} MHz • GPU ${if(s.telemetry.gpuHz>=0)s.telemetry.gpuHz/1000000 else 0} MHz")
        OutlinedTextField(value=keyInput,onValueChange={keyInput=it},label={Text("Gemini API key")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="SAVE"},enabled=bridgeOp==null&&keyInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE / REPLACE")}
            Button(onClick={bridgeOp="STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}
            Button(onClick={bridgeOp="DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}
        }
        OutlinedTextField(value=chatInput,onValueChange={chatInput=it.take(8000)},label={Text("Ask DJAEGER Gemini")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="CHAT"},enabled=bridgeOp==null&&chatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK GEMINI")}
            Button(onClick={bridgeOp="CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW CHAT")}
        }
        BoxCard("GEMINI CONVERSATION",chatResult+"\n\nTransport errors affect Gemini chat only; Hermes H2/kernel execution remains independently observable below.",true)
        BoxCard("AI SUMMARY LIVE",aiSummary(s));BoxCard("HERMES H2 LOCAL BRAIN LIVE",brainText,true);BoxCard("ADAPTIVE OPERATING ENVELOPE LIVE",s.envelope.ifBlank{"No envelope published yet"},true);BoxCard("DJAEGER CURRENT INTERPRETATION",retained,true);BoxCard("GEMINI HTTP STATE LIVE",s.geminiHttp.ifBlank{"No Gemini HTTP state yet"},true);BoxCard("GEMINI SERVER STATE LIVE",s.geminiServer.ifBlank{"No server state / no active backoff"},true)
    }
}
private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / transport state reported";else->"State published"};val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"UNPUBLISHED"};val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"UNPUBLISHED"};val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"};val ast=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"};val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"};val sync=envField(s.brain,"CONTROL_CENTER_SYNC").ifBlank{"UNPUBLISHED"};return "Cloud brain: $cloud • $gem\nLocal brain: $local\nAgent: A2 • $ast\nWinner: $winner • score $score\nSync: $sync\nFinal hardware authority: AI AGENT A2 → ROOT AUTHORITY"}

@Composable fun MatchedPairSyncCard(s:RuntimeState){
    val expected="DUALBRAIN-AGENT-A2-SYNC2-FIX1"
    val matched=s.moduleVersion.contains(expected)
    val state=if(matched)"MATCHED" else "MODULE UPDATE REQUIRED"
    BoxCard("DJAEGER-AI MATCHED PAIR","Control Center: v0.12.2 • Agent A2 SYNC2 FIX1\nModule: ${s.moduleVersion}\nCompatibility: $state\nExpected marker: $expected\nCloud brain: GEMINI\nLocal brain: HERMES H2\nFinal owner: AI AGENT A2",true)
}

@Composable fun AgentA2Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"UNPUBLISHED"}
    val arch=envField(s.brain,"AGENT_ARCH").ifBlank{"UNPUBLISHED"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"}
    val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"}
    val reason=envField(s.brain,"AGENT_REASON").ifBlank{"—"}
    val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"UNPUBLISHED"}
    val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"UNPUBLISHED"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"UNPUBLISHED"}
    val direct=envField(s.brain,"DIRECT_ROOT_AUTHORITY").ifBlank{"UNPUBLISHED"}
    val readback=envField(s.brain,"READBACK_REQUIRED").ifBlank{"UNPUBLISHED"}
    val rollback=envField(s.brain,"ROLLBACK_REQUIRED").ifBlank{"UNPUBLISHED"}
    val nativeRole=envField(s.brain,"NATIVE_BASELINE_ROLE").ifBlank{"UNPUBLISHED"}
    val sync=envField(s.brain,"CONTROL_CENTER_SYNC").ifBlank{"UNPUBLISHED"}
    fun yn(v:String)=when(v){"1"->"YES";"0"->"NO";else->v}
    BoxCard("AI AGENT A2 • FINAL AUTHORITY","Version: $version • Architecture: $arch\nCloud brain: $cloud\nLocal brain: $local\nThird brain: $third\nState: $state\nWinner: $winner • Score: $score\nReason: $reason\nDecision owner: AI AGENT A2\nExecution owner: AI AGENT A2\nDirect Root Authority: ${yn(direct)}\nReadback required: ${yn(readback)}\nRollback required: ${yn(rollback)}\nNative baseline: $nativeRole\nContract sync: $sync",true)
}

@Composable fun History(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){DecisionCard(s.latestDecision);PlanCard(s.latestPlan);BoxCard("DECISION LEDGER • LAST 16",s.decisions.ifBlank{"No decisions recorded yet"},true);BoxCard("PLAN HISTORY • LAST 16",s.plans.ifBlank{"No plans recorded yet"},true)}}
@Composable fun DecisionCard(d:DecisionRecord?){if(d==null)BoxCard("LATEST AI DECISION","No decision parsed yet") else BoxCard("LATEST AI DECISION","ID: ${d.id}\nGame: ${d.game} • Scene: ${d.scene}\nProfile: ${d.profile}\nBudgets L/B/G: ${d.little} / ${d.big} / ${d.gpu}\nOutcome: ${d.outcome}\nPred FPS/Skin: ${d.predFps} / ${d.predSkin}\nActual FPS/Skin: ${d.actualFps} / ${d.actualSkin}\nWindow: ${d.window}")}
@Composable fun PlanCard(p:PlanRecord?){if(p==null)BoxCard("LATEST PLAN","No plan parsed yet") else BoxCard("LATEST PLAN","State: ${p.state} • Score: ${p.score}\nReason: ${p.reason}\nMode/Profile: ${p.mode} / ${p.profile}\nLittle: ${p.lmin}–${p.lmax}\nBig: ${p.bmin}–${p.bmax}\nGPU: ${p.gmin}–${p.gmax}")}
@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){BoxCard("MONITOR INVARIANTS","No direct hardware writes from Control Center\nControls use typed djaeger-ai interfaces only\nExactly two brains: Gemini + Hermes H2\nNo third AI brain\nAI Agent A2 is final decision/execution owner\nRoot Authority performs verified hardware transaction\nNo network/game traffic manipulation");BoxCard("RUNTIME HEALTH","Root: ${if(s.root)"OK" else "UNAVAILABLE"}\nModule: ${if(s.installed)"FOUND" else "NOT FOUND"}\nController: ${if(s.controllerPid.isNotBlank())"PID ${s.controllerPid}" else "NOT REPORTED"}\nPredictor: ${if(s.predictorPid.isNotBlank())"PID ${s.predictorPid}" else "NOT REPORTED"}\nRuntime status: ${if(stale)"STALE / NOT REPORTED" else "FRESH"}\nPower telemetry: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("RESTORATION WATCH","Control Center does not write CPU/GPU nodes directly. Typed requests are executed by AI Agent A2 / Root Authority. Original-state restoration is owned by DJAEGER Root Authority with session/boot validation, bounded retry, and hardware readback.")}}
@Composable fun Logs(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState())){BoxCard("LIVE CONTROLLER LOG • LAST 120",s.log.ifBlank{"No controller log available"},true)}}
@Composable fun Metric(label:String,value:String,m:Modifier=Modifier){Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(value,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}
@Composable fun BoxCard(title:String,text:String,mono:Boolean=false){val clipboard=LocalClipboardManager.current;Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.labelLarge);TextButton(onClick={clipboard.setText(AnnotatedString("DJAEGER Control Center v0.12.2 A2 SYNC2 FIX1\n["+title+"]\n"+text))}){Text("COPY",maxLines=1)}};Spacer(Modifier.height(7.dp));Text(text,color=Color(0xFFE6EAF0),fontFamily=if(mono)FontFamily.Monospace else FontFamily.Default,style=MaterialTheme.typography.bodyMedium)}}}

// CI_BASELINE_MARKER: v0.12.2 • AGENT A2 SYNC2 FIX1
