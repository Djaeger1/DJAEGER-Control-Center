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
private val Bg=Color(0xFF090B10); private val Card=Color(0xFF121722); private val Green=Color(0xFF43E38A); private val Muted=Color(0xFF98A2B3); private val Amber=Color(0xFFFFC857); private val Red=Color(0xFFFF6B6B); private val GameTitlePink=Color(0xFFFF8CC6); private val AppTitleLightBlue=Color(0xFF7DD3FC)

data class Sample(val fps:Double,val frame:Double,val cpu:Float,val gpu:Float,val skin:Float,val bat:Float)

private fun sampleTemp(value:Int)=if(value>=0)value.toFloat() else Float.NaN
private fun tempText(value:Int)=if(value>=0)"$value°C" else "—"
private fun positiveText(value:Double,suffix:String)=if(value>0)"%.1f%s".format(value,suffix) else "—"
private fun jankText(value:Double)=if(value.isFinite()&&value>=0.0)"%.1f%%".format(value) else "—"
private fun runtimeStateStale(s:RuntimeState):Boolean{
    return s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>15L
}
private fun positiveLongText(value:Long,divisor:Long,suffix:String)=if(value>0)"${value/divisor}$suffix" else "—"
private fun stat3(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f / %.1f%s".format(values.average(),values.minOrNull()?:0.0,values.maxOrNull()?:0.0,unit)
private fun stat2(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f%s".format(values.average(),values.maxOrNull()?:0.0,unit)
private fun hccPresetFromBlock(block:String):String{
    block.lineSequence().forEach{line->
        val x=line.trim()
        if(x.startsWith("COMFORT_PRESET=")||x.startsWith("HUMAN_COMFORT_PRESET=")){
            return x.substringAfter('=').trim().trim('\'', '"').uppercase()
        }
    }
    return ""
}
@Composable private fun HccPresetButton(label:String,selected:Boolean,enabled:Boolean,onClick:()->Unit,modifier:Modifier=Modifier){
    if(selected) Button(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
    else OutlinedButton(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
}
@Composable private fun HccFeedbackButton(label:String,flash:Boolean,enabled:Boolean,onClick:()->Unit,modifier:Modifier=Modifier){
    if(flash) Button(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
    else OutlinedButton(onClick=onClick,enabled=enabled,modifier=modifier){Text(label,style=MaterialTheme.typography.labelSmall)}
}

@Composable fun App(){val repo=remember{DjaegerRepository()};val context=androidx.compose.ui.platform.LocalContext.current;val notifier=remember{BugNotifier(context)};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()};var manualRefresh by remember{mutableIntStateOf(0)};var refreshBusy by remember{mutableStateOf(false)};var refreshStatus by remember{mutableStateOf("LOCAL AUTO 3s")}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner){lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){var lastSyncAt=0L;while(true){var fresh=repo.snapshot();val nowSec=System.currentTimeMillis()/1000;if(envField(fresh.controlCenterSync,"PAIR_VERIFIED")!="YES"&&nowSec-lastSyncAt>=15){repo.synchronizeLocal();lastSyncAt=nowSec;fresh=repo.snapshot()};state=fresh;notifier.notifyIfNeeded(state.bugHealth);if(state.root&&state.installed&&state.active=="1"&&state.sampleFresh){with(state.telemetry){samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)));while(samples.size>60)samples.removeAt(0)}};delay(3000)}}}
    LaunchedEffect(manualRefresh){if(manualRefresh>0){refreshBusy=true;val beforeGen=envField(state.controlCenterSync,"SNAPSHOT_GENERATION");val sync=repo.synchronizeLocal();val fresh=repo.snapshot();state=fresh;notifier.notifyIfNeeded(fresh.bugHealth);val afterGen=envField(fresh.controlCenterSync,"SNAPSHOT_GENERATION");val now=SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date());refreshStatus=when{!sync.first->"LOCAL SYNC ERROR • $now";fresh.error.isNotBlank()->"LOCAL SNAPSHOT ERROR • $now";afterGen.isNotBlank()&&afterGen!=beforeGen->"LOCAL SYNCED • GEN $afterGen • $now";else->"LOCAL ACK WITHOUT NEW GEN • $now"};refreshBusy=false}}
    MaterialTheme(colorScheme=darkColorScheme(primary=Green,background=Bg,surface=Card)){Column(Modifier.fillMaxSize().background(Bg).padding(16.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Column(Modifier.weight(1f)){Text("DJAEGER",fontWeight=FontWeight.Black,style=MaterialTheme.typography.headlineMedium,color=MaterialTheme.colorScheme.onBackground);Text("CONTROL CENTER",color=Muted);Text(refreshStatus,color=Muted,style=MaterialTheme.typography.labelSmall)};Button(onClick={if(!refreshBusy)manualRefresh++},enabled=!refreshBusy){Text(if(refreshBusy)"REFRESHING…" else "REFRESH LOCAL")}};Spacer(Modifier.height(12.dp));ScrollableTabRow(selectedTabIndex=tab,containerColor=Bg,edgePadding=0.dp){listOf("Overview","Session","Charts","AI","History","Safety","Bug & Health","Logs").forEachIndexed{i,n->Tab(selected=tab==i,onClick={tab=i},text={Text(n)})}};Spacer(Modifier.height(12.dp));when(tab){0->Overview(state);1->Session(state,samples,repo);2->Charts(state,samples);3->AI(state);4->History(state);5->Safety(state);6->BugHealth(state.bugHealth);else->Logs(state)}}}}


private fun thoughtField(raw:String,key:String):String = raw.lineSequence().firstOrNull{it.startsWith("$key=")}?.substringAfter('=')?.trim()?.trim('\'') ?: ""
private fun envField(raw:String,key:String):String = thoughtField(raw,key)
private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI • ADVISORY REASONER"
    "OBSERVER_LOCAL"->"LOCAL OBSERVER • DEVICE TRUTH"
    "HERMES_LOCAL","HERMES_H2"->"HERMES LOCAL • VALIDATOR / REVIEWER"
    "NONE"->"NONE • NATIVE FAILSAFE"
    else->raw.ifBlank{"—"}
}
private fun ageLabel(raw:String):String{
    val n=raw.toLongOrNull()?:return "—"
    if(n<0)return "—"
    return when{n<60->"${n}s";n<3600->"${n/60}m ${n%60}s";else->"${n/3600}h ${(n%3600)/60}m"}
}

@Composable fun ThoughtsCard(s:RuntimeState){
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")}
    val finalSource=envField(s.brain,"FINAL_SOURCE").ifBlank{envField(s.brain,"SOURCE")}
    val brainMode=envField(s.brain,"BRAIN_MODE").ifBlank{envField(s.brain,"MODE")}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudConnection=envField(s.brain,"GEMINI_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider="GEMINI"
    val cloudControlProvider=envField(s.brain,"CLOUD_CONTROL_PROVIDER").ifBlank{
        when{
            currentBrain=="GEMINI" -> "GEMINI"
            envField(s.brain,"HERMES_BACKEND").equals("CLOUD",true) && (currentBrain=="HERMES_H2"||currentBrain=="HERMES_LOCAL") -> "HERMES_CLOUD"
            else -> "NONE"
        }
    }
    val cloudPlanProvider=envField(s.brain,"CLOUD_PLAN_PROVIDER").ifBlank{
        when{
            cloudControlProvider=="GEMINI" && cloudState!="NOT_USED" && cloudState!="UNAVAILABLE" -> "GEMINI"
            cloudControlProvider=="HERMES_CLOUD" && cloudState!="NOT_USED" && cloudState!="UNAVAILABLE" -> "HERMES_CLOUD"
            else -> "NONE"
        }
    }
    val cloudInControl=when(cloudControlProvider.uppercase()){
        "GEMINI" -> "GEMINI"
        "HERMES_CLOUD","HERMES CLOUD" -> "HERMES CLOUD"
        else -> "NO"
    }
    val cloudPlan=when(cloudPlanProvider.uppercase()){
        "GEMINI" -> "GEMINI"
        "HERMES_CLOUD","HERMES CLOUD" -> "HERMES CLOUD"
        else -> "NOT_USED"
    }
    val thoughtSrc=envField(s.thoughts,"SOURCE")
    val thoughtStatus=envField(s.thoughts,"STATUS").ifBlank{"WAITING"}
    val thoughtFresh=envField(s.brain,"THOUGHT_FRESH")
    val thoughtAge=envField(s.brain,"THOUGHT_AGE_SEC")
    val conf=envField(s.thoughts,"CONFIDENCE")
    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}
    val isFresh=thoughtFresh=="1"
    val thoughtTitle=when{
        thoughtSrc=="GEMINI"&&isFresh->"PEMIKIRAN GEMINI"
        thoughtSrc=="GEMINI"->"LAST GEMINI THOUGHT"
        thoughtSrc=="HERMES_H2"->"PEMIKIRAN HERMES H2"
        else->"PEMIKIRAN DJAEGER"
    }
    val statusLabel=when{
        thoughtSrc=="GEMINI"&&!isFresh->"STALE • age ${ageLabel(thoughtAge)}"
        thoughtSrc=="GEMINI"->cloudConnection
        else->thoughtStatus
    }
    val geminiLine=if(cloudProvider=="GEMINI") "GEMINI • $cloudConnection" else cloudConnection
    val memUsed=envField(s.memoryStatus,"USED_BYTES").toLongOrNull()?:0L
    val memMax=envField(s.memoryStatus,"MAX_BYTES").toLongOrNull()?:0L
    val rows=envField(s.memoryStatus,"LEDGER_ROWS").ifBlank{"0"}
    val hw=envField(s.memoryStatus,"HARDWARE_OUTCOME_ROWS").ifBlank{"0"}
    val mem=if(memMax>0L) "Memory: %.1f / %.0f MiB • knowledge %s • outcomes %s".format(memUsed/1048576.0,memMax/1048576.0,rows,hw) else "Memory: UNAVAILABLE • knowledge $rows • outcomes $hw"
    val body="Gemini: $geminiLine\nActive brain: ${brainLabel(currentBrain)}\nCloud in control: $cloudInControl\nBrain mode: ${brainMode.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nCloud plan: $cloudPlan\n\n$thoughtTitle • $statusLabel\n$text\n\nThought source: ${thoughtSrc.ifBlank{"—"}}\nConfidence: ${conf.ifBlank{"—"}}%\n$mem"
    BoxCard("THOUGHT",body,true)
}

@Composable fun AgentRebuild3Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"UNPUBLISHED"}
    val role=envField(s.brain,"AGENT_ROLE").ifBlank{"UNPUBLISHED"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val input=envField(s.brain,"AGENT_INPUT_SOURCE").ifBlank{"UNPUBLISHED"}
    val decisionAuth=envField(s.brain,"AGENT_DECISION_AUTHORITY").ifBlank{"UNPUBLISHED"}
    val executionOwner=envField(s.brain,"AGENT_EXECUTION_OWNER").ifBlank{"UNPUBLISHED"}
    val hwAuthority=envField(s.brain,"AGENT_HARDWARE_AUTHORITY").ifBlank{"UNPUBLISHED"}
    val truthSource=envField(s.brain,"AGENT_HARDWARE_TRUTH_SOURCE").ifBlank{"UNPUBLISHED"}
    val truthAuthority=envField(s.brain,"AGENT_HARDWARE_TRUTH_AUTHORITY").ifBlank{"UNPUBLISHED"}
    val mustObey=envField(s.brain,"AGENT_MUST_OBEY_ACTIVE_BRAIN").ifBlank{"UNPUBLISHED"}
    val canChoose=envField(s.brain,"AGENT_CAN_CHOOSE_BRAIN").ifBlank{"UNPUBLISHED"}
    val canOverride=envField(s.brain,"AGENT_CAN_OVERRIDE_BRAIN").ifBlank{"UNPUBLISHED"}
    val backend=envField(s.brain,"AGENT_EXECUTION_BACKEND").ifBlank{"UNPUBLISHED"}
    val validation=envField(s.brain,"AGENT_LAST_VALIDATION").ifBlank{"UNKNOWN"}
    val readback=envField(s.brain,"AGENT_LAST_READBACK").ifBlank{"UNKNOWN"}
    val priority=envField(s.brain,"DECISION_PRIORITY").ifBlank{"UNPUBLISHED"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"UNPUBLISHED"}
    val syncContract=envField(s.controlCenterSync,"CONTRACT")
    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE")
    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE")
    val syncKernel=envField(s.controlCenterSync,"HERMES_KERNEL")
    val syncSysfs=envField(s.controlCenterSync,"AGENT_SYSFS")
    val syncGameRegistry=envField(s.controlCenterSync,"GAME_REGISTRY")
    val syncShared=envField(s.controlCenterSync,"SHARED_INTELLIGENCE")
    val geminiScope=envField(s.controlCenterSync,"GEMINI_INTELLIGENCE_SCOPE")
    val hermesScope=envField(s.controlCenterSync,"HERMES_INTELLIGENCE_SCOPE")
    val geminiReasoningLimit=envField(s.controlCenterSync,"GEMINI_REASONING_LIMIT")
    val hermesTeacherLoop=envField(s.controlCenterSync,"HERMES_TEACHER_LOOP")
    val syncHermesCloud=envField(s.controlCenterSync,"HERMES_CLOUD")
    val syncHermesCloudRole=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE")
    val syncHermesBackendPriority=envField(s.controlCenterSync,"HERMES_BACKEND_PRIORITY")
    val syncWorkloadFinal=envField(s.controlCenterSync,"WORKLOAD_FINAL")
    val syncDualRegistry=envField(s.controlCenterSync,"DUAL_REGISTRY")
    val syncPreexecGuard=envField(s.controlCenterSync,"PREEXEC_WORKLOAD_GUARD")
    val adaptiveContract=syncContract=="DJAEGER_AI_ADAPTIVE_V2"
    val workloadActive=envField(s.workloadFinal,"STATUS")=="ACTIVE"
    val pairVerified=envField(s.controlCenterSync,"PAIR_VERIFIED")=="YES"
    val exactMatched=adaptiveContract&&pairVerified&&syncModule=="203"&&syncCc=="104"
    val identityMatched=!adaptiveContract&&s.installed&&s.moduleVersion.contains("HERMESCLOUD1",true)&&workloadActive
    val matched=s.installed&&(exactMatched||identityMatched)
    val matchText=when{exactMatched->"YES • VERIFIED HANDSHAKE";identityMatched->"YES • LEGACY IDENTITY";!s.installed->"NO • MODULE NOT INSTALLED";adaptiveContract->"NO • HANDSHAKE NOT VERIFIED";else->"CHECKING • CONTRACT NOT PUBLISHED"}
    val body="Matched module: $matchText\nRole: $role\nState: $state\nActive command source: $input\nDecision authority: $decisionAuth\nExecution owner: $executionOwner\nHardware authority: $hwAuthority\nHardware truth: $truthAuthority • $truthSource\nMust obey active brain: $mustObey\nCan choose brain: $canChoose\nCan override brain: $canOverride\nWriter chain: $backend\nLast validation: $validation\nLast readback: $readback\nDecision priority: $priority\nShared intelligence: ${syncShared.ifBlank{"UNPUBLISHED"}}\nGemini intelligence: ${geminiScope.ifBlank{"UNPUBLISHED"}}\nHermes intelligence: ${hermesScope.ifBlank{"UNPUBLISHED"}}\nGemini reasoning limit from Hermes feature set: ${geminiReasoningLimit.ifBlank{"UNPUBLISHED"}}\nHermes teacher loop: ${hermesTeacherLoop.ifBlank{"UNPUBLISHED"}}\nHERMES Cloud: ${syncHermesCloud.ifBlank{"UNPUBLISHED"}}\nHERMES Cloud role: ${syncHermesCloudRole.ifBlank{"UNPUBLISHED"}}\nHERMES backend priority: ${syncHermesBackendPriority.ifBlank{"UNPUBLISHED"}}\nWorkload final: ${syncWorkloadFinal.ifBlank{"UNPUBLISHED"}}\nDual registry: ${syncDualRegistry.ifBlank{"UNPUBLISHED"}}\nPre-exec workload guard: ${syncPreexecGuard.ifBlank{"UNPUBLISHED"}}\nImmediate Gemini facts: DELTA / EVENT DRIVEN\nThird brain: $third"
    BoxCard(if(adaptiveContract) "DJAEGER AI AGENT • LOCAL GATED SYSFS" else "AI AGENT • SYSFS1 • FULL HARDWARE CONTROLLER",body,true)
}

private fun currentRange(raw:String,unit:String):String{
    val v=raw.trim()
    return if(v.isBlank()||v.contains("NA")) "—" else "$v $unit"
}

private fun planRange(a:String,b:String,unit:String):String{
    val x=a.trim(); val y=b.trim()
    return if(x.isBlank()||y.isBlank()||x.equals("NA",true)||y.equals("NA",true)) "—" else "$x-$y $unit"
}

@Composable fun KernelAgentSyncCard(s:RuntimeState){
    val adaptiveContract=envField(s.controlCenterSync,"CONTRACT")=="DJAEGER_AI_ADAPTIVE_V2"
    val kState=envField(s.hermesKernel1,"STATE").ifBlank{"UNAVAILABLE"}
    val kStrategy=envField(s.hermesKernel1,"STRATEGY").ifBlank{"—"}
    val kBottleneck=envField(s.hermesKernel1,"BOTTLENECK").ifBlank{"—"}
    val kCaps=envField(s.hermesKernel1,"CAPABILITIES_TOTAL").ifBlank{envField(s.agentSysfs1Capability,"TOTAL").ifBlank{"0"}}
    val kActs=envField(s.hermesKernel1,"ACTUATORS_TOTAL").ifBlank{envField(s.agentSysfs1Capability,"ACTUATORS").ifBlank{"0"}}
    val kActions=envField(s.hermesKernel1,"ACTION_COUNT").ifBlank{"0"}
    val kMem=envField(s.hermesKernel1,"MEMORY_SAMPLES").ifBlank{"0"}
    val kOk=envField(s.hermesKernel1,"MEMORY_SUCCESS").ifBlank{"0"}
    val kBad=envField(s.hermesKernel1,"MEMORY_FAILED").ifBlank{"0"}
    val execStatus=envField(s.agentSysfs1Execution,"STATUS").ifBlank{"IDLE / NO EXECUTION YET"}
    val execStrategy=envField(s.agentSysfs1Execution,"STRATEGY_ID").ifBlank{"—"}
    val execCount=envField(s.agentSysfs1Execution,"ACTION_COUNT").ifBlank{"0"}
    val execApplied=envField(s.agentSysfs1Execution,"APPLIED_COUNT").ifBlank{"0"}
    val execFail=envField(s.agentSysfs1Execution,"FAILURE").ifBlank{"NONE"}
    val rootOwner=envField(s.hermesKernel1,"ROOT_AUTHORITY_OWNER").ifBlank{if(adaptiveContract)"STOCK_KERNEL" else "AI_AGENT"}
    val sysfsOwner=envField(s.hermesKernel1,"SYSFS_OWNER").ifBlank{if(adaptiveContract)"STOCK_KERNEL" else "AI_AGENT"}
    val executionOwner=if(adaptiveContract) "LOCAL VALIDATED EXECUTOR" else "AI_AGENT"
    val body="Hermes kernel model: $kState\nStrategy: $kStrategy\nBottleneck: $kBottleneck\nKernel capabilities: $kCaps • writable actuators: $kActs\nPlanned actions: $kActions\nHistorical kernel outcomes: $kMem • success $kOk • failed $kBad\n\nAgent SYSFS1 execution: $execStatus\nStrategy ID: $execStrategy\nActions: $execApplied / $execCount applied\nFailure: $execFail\nRoot Authority owner: $rootOwner\nSysfs owner: $sysfsOwner\nExecution owner: $executionOwner\nHermes direct hardware writes: 0"
    BoxCard(if(adaptiveContract) "HERMES KERNEL REVIEW ↔ LOCAL EXECUTOR" else "HERMES KERNEL1 ↔ AI AGENT SYSFS1",body,true)
}

@Composable fun HermesStatusCard(s:RuntimeState){
    val cloudState=envField(s.brain,"HERMES_CLOUD_STATE").ifBlank{"UNAVAILABLE"}
    val cloudAuth=envField(s.brain,"HERMES_CLOUD_AUTH").ifBlank{"UNKNOWN"}
    val cloudRoute=envField(s.brain,"HERMES_CLOUD_ROUTE").uppercase()
    val route=if(cloudRoute=="FAST"||cloudRoute=="SMART"||cloudRoute=="DEEP"||cloudRoute=="CLOUD") cloudRoute else "LOCAL"
    val cloud=envField(s.brain,"HERMES_CONNECTION_STATUS").ifBlank{
        when(cloudState){ "ONLINE","APPROVED","REJECTED"->"ONLINE";"REACHABLE_IDLE"->"REACHABLE • AUTH UNVERIFIED";"NO_KEY"->"NOT_CONFIGURED";"AUTH_ERROR"->"AUTH_ERROR";"HTTP_ERROR","FAILED","UNAVAILABLE","OFFLINE"->"OFFLINE";else->if(cloudAuth=="CONFIGURED")"READY" else if(cloudAuth=="CONFIGURED_UNVERIFIED")"REACHABLE • AUTH UNVERIFIED" else "NOT_CONFIGURED" }
    }
    val used=envField(s.brain,"HERMES_NEURON_USED_EST").ifBlank{"UNAVAILABLE"}
    val limit=envField(s.brain,"HERMES_NEURON_LIMIT").ifBlank{"UNAVAILABLE"}
    val neuronLine=if(used.toLongOrNull()!=null&&limit.toLongOrNull()!=null) "$used / $limit • EST" else "UNAVAILABLE • provider does not report usage"
    val hermesFresh=envField(s.supervisor,"HERMES").startsWith("FRESH:")
    val localState=when{!s.installed->"OFFLINE";hermesFresh->"ONLINE";else->"STALE"}
    BoxCard("HERMES: $localState","Local    $localState\nRoute    $route\nCloud    $cloud\nNeurons  $neuronLine",true)
}

@Composable fun HermesCloudCard(s:RuntimeState){
    val adaptiveContract=envField(s.controlCenterSync,"CONTRACT")=="DJAEGER_AI_ADAPTIVE_V2"
    val backend=envField(s.brain,"HERMES_BACKEND").ifBlank{"LOCAL"}
    val state=envField(s.brain,"HERMES_CLOUD_STATE").ifBlank{"UNAVAILABLE"}
    val auth=envField(s.brain,"HERMES_CLOUD_AUTH").ifBlank{"UNKNOWN"}
    val route=envField(s.brain,"HERMES_CLOUD_ROUTE").ifBlank{"—"}
    val model=envField(s.brain,"HERMES_CLOUD_MODEL").ifBlank{"—"}
    val latency=envField(s.brain,"HERMES_CLOUD_LATENCY_MS").ifBlank{"—"}
    val http=envField(s.brain,"HERMES_CLOUD_HTTP_CODE").ifBlank{"—"}
    val fallback=envField(s.brain,"HERMES_CLOUD_FALLBACK_USED").ifBlank{"NO"}
    val requestId=envField(s.brain,"HERMES_CLOUD_REQUEST_ID").ifBlank{"—"}
    val reason=envField(s.brain,"HERMES_CLOUD_REASON").ifBlank{"—"}
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{"—"}
    val contract=envField(s.controlCenterSync,"HERMES_CLOUD").ifBlank{"UNPUBLISHED"}
    val role=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE").ifBlank{"REMOTE_BACKEND_OF_HERMES_H2_NOT_THIRD_BRAIN"}
    val policyLine=if(adaptiveContract) "Gemini candidate → Hermes Local guard → ONE HERMES Cloud review → shadow evidence → local executor → readback/rollback" else "Gemini primary → HERMES H2 cloud → HERMES H2 local → native failsafe"
    val executorLine=if(adaptiveContract) "Hardware executor: LOCAL GATED ONLY • cloud direct hardware authority NONE" else "Hardware executor: AI AGENT A1 ONLY"
    val body="Contract: $contract\nEndpoint: module-configured • secret-safe status only\nHERMES H2 backend: $backend\nCloud state: $state\nAccess key: $auth • secret never displayed\nRoute: $route\nModel: $model\nLatency: $latency ms • HTTP: $http\nReason: $reason\nCloud tier fallback used: $fallback\nRequest ID: $requestId\nCurrent brain: $currentBrain\nRole: $role\nPolicy: $policyLine\nCloud direct hardware authority: NONE\n$executorLine"
    BoxCard("HERMES CLOUD • ONE HERMES • HERMESCLOUD1",body,true)
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
    val mathState=envField(s.hermesMath,"STATE").ifBlank{"UNAVAILABLE"}
    val mathVerify=envField(s.hermesMath,"VERIFY").ifBlank{"—"}
    val mathSanity=envField(s.hermesMath,"INPUT_SANITY").ifBlank{"—"}
    val mathFrame=envField(s.hermesMath,"TARGET_FRAME_MS").ifBlank{"—"}
    val mathFpsErr=envField(s.hermesMath,"FPS_ERROR").ifBlank{"—"}
    val mathHeadroom=envField(s.hermesMath,"THERMAL_HEADROOM_C").ifBlank{"—"}
    val mathThermal=envField(s.hermesMath,"THERMAL_PRESSURE").ifBlank{"—"}
    val mathFramePressure=envField(s.hermesMath,"FRAME_PRESSURE").ifBlank{"—"}
    val mathControl=envField(s.hermesMath,"CONTROL_PRESSURE").ifBlank{"—"}
    val syncContract=envField(s.controlCenterSync,"CONTRACT").ifBlank{"UNPUBLISHED"}
    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE").ifBlank{"—"}
    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE").ifBlank{"—"}
    val syncMatched=(syncContract=="DJAEGER_AI_ADAPTIVE_V2"&&envField(s.controlCenterSync,"PAIR_VERIFIED")=="YES"&&syncModule=="203"&&syncCc=="104")||(syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_DUALREG3_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1_APPREBUILD4_MAXVALUE1"&&syncModule=="129659"&&syncCc=="12263")
    val currentBrain=envField(s.brain,"CURRENT_BRAIN")
    val finalSource=envField(s.brain,"FINAL_SOURCE")
    val displayState=when(hState){
        "VALID"->if(currentBrain=="HERMES_H2"||currentBrain=="HERMES_LOCAL") "ACTIVE DEPUTY" else "READY DEPUTY"
        "STANDBY_GEMINI_ONLINE"->"STANDBY • GEMINI VALID"
        "LOW_CONFIDENCE"->"LEARNING • LOW CONFIDENCE"
        "UNAVAILABLE"->"UNAVAILABLE"
        else->hState
    }
    val hBackend=envField(s.brain,"HERMES_BACKEND").ifBlank{"LOCAL"}
    val authority=when(currentBrain){"GEMINI"->"GEMINI ADVISORY PROPOSAL • NO DIRECT HARDWARE WRITES";"AI_CONSENSUS"->"CONSENSUS RESULT • LOCAL VALIDATOR / EXECUTOR OWNS HARDWARE";else->"HERMES/LOCAL REVIEW • backend $hBackend • NO DIRECT HARDWARE WRITES"}
    val body="State: $displayState\nMode: $hMode\nProfile: $hProfile\nConfidence: $hConfidence%\nVariable: $hVariable\nValue: $hValue\nVariable state: $hVariableState\nContext samples: $hSamples\nContext success rate: $hRate%\nEvidence scope: $hScope\nEvidence filter: $hFilter\nBrain source: ${currentBrain.ifBlank{"—"}}\nFinal source: ${finalSource.ifBlank{"—"}}\nAuthority: $authority\nReason: $hReason\n\nLANG3: CONVERSATIONAL • semantic planner + continuity + anti-repeat\nMATH1: $mathState • verify $mathVerify • sanity $mathSanity\nTarget frame: $mathFrame ms • FPS error: $mathFpsErr\nThermal headroom: $mathHeadroom °C • thermal/frame/control pressure: $mathThermal/$mathFramePressure/$mathControl\nControl Center sync: ${if(syncMatched) "MATCHED" else "MISMATCH/WAITING"} • $syncContract • module vc$syncModule / app vc$syncCc"
    BoxCard("HERMES H2 • KERNEL1 • LANG3 + MATH1",body,true)
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
    val cloudConnection=envField(s.brain,"GEMINI_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudScore=envField(s.brain,"CLOUD_PLAN_SCORE").ifBlank{"0"}
    val cloudReason=envField(s.brain,"CLOUD_PLAN_REASON").ifBlank{"—"}
    val hermesState=envField(s.brain,"HERMES_PROPOSAL_STATE").ifBlank{envField(s.brain,"HERMES_STATE").ifBlank{"—"}}
    val hermesConf=envField(s.brain,"HERMES_PROPOSAL_CONFIDENCE").ifBlank{envField(s.brain,"HERMES_CONFIDENCE").ifBlank{"0"}}
    val srValidation=envField(s.strategyResult,"VALIDATION")
    val srReadback=envField(s.strategyResult,"READBACK")
    val srOutcome=envField(s.strategyResult,"OUTCOME")
    val validation=if(srValidation.isNotBlank()) "$srValidation • readback=${srReadback.ifBlank{"—"}} • outcome=${srOutcome.ifBlank{"—"}}" else "LOCAL VALIDATOR / FAIL-CLOSED"
    val body="Gemini: $cloudConnection\nTruth: CURRENT BRAIN / FUSED\nCloud proposal: $cloudState • ${cloudScore}%\nCloud reason: $cloudReason\nHermes proposal: $hermesState • ${hermesConf}%\nCurrent brain: ${brainLabel(currentBrain)}\nBrain decision: ${brainMode.ifBlank{"—"}}\nBrain profile: ${brainProfile.ifBlank{"—"}}\nFinal profile / mode: $finalProfile / $execMode\nFinal source: ${finalSource.ifBlank{"—"}}\nFinal adjustment: $adjustment\nUser mode: ${s.userMode}\nCPU little: ${currentRange(little,"kHz")}\nCPU big: ${currentRange(big,"kHz")}\nGPU: ${currentRange(gpu,"MHz")}\nValidasi Local AI: $validation"
    BoxCard("STRATEGI",body,true)
}

private fun registryPreview(raw:String,max:Int=8):String{
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
    val paired=(syncContract=="DJAEGER_AI_ADAPTIVE_V2"&&envField(s.controlCenterSync,"PAIR_VERIFIED")=="YES"&&syncModule=="203"&&syncCc=="104")||(syncContract.endsWith("WORKLOADFINAL1")&&syncModule=="129659"&&syncCc=="12263"&&finalState=="ACTIVE")

    val pairLabel=if(syncContract=="DJAEGER_AI_ADAPTIVE_V2") "VERIFIED • MODULE 203 / APP 104" else "VC129659 / VC12263"
    val body="Current: $cls • $pkg\nProfile: $profile • Subject: $subject\nReasoning: $domain\nGame semantics: $gameSem\nFrame semantics: $frameSem\nClassifier: $source • confidence $confidence%\n\nFinal enforcement: $finalState\nDual registry: $dual • conflicts $conflicts\nExecution scope: $execScope\nAPP game policy: $appPolicy\nSYSTEM game policy: $systemPolicy\nUNKNOWN game policy: $unknownPolicy\nStale policy: $stale\nLearning isolation: $learning\n\nShadow domain gates: GAME $gateGame • APP $gateApp • SYSTEM $gateSystem\nLatest proposal: $proposalSource • $proposalClass • $proposalPkg\nBinding: $proposalDecision • $proposalReason\nPre-exec guard: $guardDecision • $guardReason\n\nControl Center pair: ${if(paired)"MATCHED • $pairLabel" else "CHECKING / NOT MATCHED"}"
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
    val body="Final workload enforcement: $finalState\nAPP→game policy: $app\nSYSTEM→game policy: $system\nUNKNOWN→game policy: $unknown\nStale policy: $stale\nRoot Authority changed: $root\nSYSFS authority changed: $sysfs\nRescue path changed: $rescue\nControl Center authority: UI/telemetry only • local gated executor owns approved SYSFS writes"
    BoxCard("WORKLOAD ENFORCEMENT SAFETY",body,true)
}

@Composable fun Overview(s:RuntimeState){val power=if(s.telemetry.powerMw>=0)"%.1f mW".format(s.telemetry.powerMw) else "—";val current=if(s.telemetry.currentUa>0)"${s.telemetry.currentUa} µA" else "—";val voltage=if(s.telemetry.voltageUv>0)"${s.telemetry.voltageUv} µV" else "—";Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);ThoughtsCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS",positiveText(s.telemetry.fps,""),Modifier.weight(1f));Metric("Frame",positiveText(s.telemetry.frameMs," ms"),Modifier.weight(1f));Metric("Jank",jankText(s.telemetry.jank),Modifier.weight(1f))};ThermalRow(s);NetworkCard(s.network);StrategyCard(s);HermesStatusCard(s);AgentRebuild3Card(s);HermesCloudCard(s);KernelAgentSyncCard(s);HermesCard(s);HumanComfortHcc1Card(s);ContextVNextCard(s);MemoryVNextCard(s);ReasoningV2Card(s);SkillsVNextCard(s);LearningResearchV2Card(s);OutcomeLearningCard(s);StrategyCompositionCard(s);DecisionPipelineCard(s);BoxCard("PERFORMANCE","Little current: ${positiveLongText(s.telemetry.littleKhz,1000," MHz")}\nBig current: ${positiveLongText(s.telemetry.bigKhz,1000," MHz")}\nGPU current: ${positiveLongText(s.telemetry.gpuHz,1_000_000," MHz")}\nLearned Little: ${s.strategy.cpuLittleMin}–${s.strategy.cpuLittleMax} kHz\nLearned Big: ${s.strategy.cpuBigMin}–${s.strategy.cpuBigMax} kHz\nLearned GPU: ${s.strategy.gpuMin}–${s.strategy.gpuMax} Hz\nProfile: ${s.telemetry.profile}\nP95/P99: ${positiveText(s.telemetry.p95," ms")} / ${positiveText(s.telemetry.p99," ms")}");BoxCard("POWER","${s.telemetry.batteryStatus} • $power\n$current • $voltage\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true);WorkloadIntelligenceCard(s)}}
private fun compactModuleVersion(raw:String):String=when{
    raw.contains("adaptive",true)->"DJAEGER AI Adaptive • device learning • no fixed preset"
    raw.contains("LOOPFIX1",true)&&raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1 • LOOPFIX1"
    raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1"
    raw.contains("ATTR1",true)&&raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1"
    raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • MATH1"
    raw.contains("MWFIX1",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX1 • MATH1"
    raw.contains("MWFIX1",true)&&raw.contains("LANG2",true)->"v12.9.50 • REBUILD3 • LANG2 • MWFIX1"
    raw.contains("REBUILD3-LANG2",true)->"v12.9.50 • REBUILD3 • LANG2"
    raw.contains("REBUILD3",true)->"v12.9.50 • REBUILD3"
    else->raw
}
@Composable fun StatusCard(s:RuntimeState){
    val stale=runtimeStateStale(s)
    val engine=if(stale) "STALE" else "LIVE"
    val workloadClass=envField(s.workloadContext,"WORKLOAD_CLASS").ifBlank{envField(s.workloadContext,"SUBJECT_CLASS")}.uppercase()
    val workloadPackage=envField(s.workloadContext,"PACKAGE").ifBlank{"UNKNOWN"}
    val workloadProfile=envField(s.workloadContext,"WORKLOAD_PROFILE").ifBlank{"UNKNOWN"}
    val sessionState=when{
        stale->"UNKNOWN / STALE"
        s.active=="1"->"GAME ACTIVE"
        workloadClass=="APP"->"APP ACTIVE • OBSERVE ONLY"
        workloadClass=="SYSTEM"->"SYSTEM ACTIVE • OBSERVE ONLY"
        else->"WAITING GAME"
    }
    val sample=when{s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"MEASURED LIVE";else->"—"}
    val game=if(s.active=="1") s.game else if(stale) "—" else "NA"
    val window=if(s.active=="1") s.window else if(stale) "—" else "INACTIVE"
    val profile=when{
        s.active=="1"->s.telemetry.profile
        workloadClass=="APP"||workloadClass=="SYSTEM"->workloadProfile
        else->"—"
    }
    val gameExecution=if(s.active=="1"&&workloadClass=="GAME") "ACTIVE" else "BLOCKED / OBSERVE ONLY"
    val age=if(s.updated>0) (System.currentTimeMillis()/1000-s.updated).coerceAtLeast(0) else -1
    val ageText=if(age>=0) "${age}s" else "—"
    BoxCard("ENGINE / SESSION",if(s.installed)"Engine: $engine • age $ageText\nSession: $sessionState\nModule: ${compactModuleVersion(s.moduleVersion)}\nGame: $game\nWindow: $window\nProfile: $profile\nWorkload: $workloadClass • $workloadPackage\nGame execution: $gameExecution\nLast device sample: $sample\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")
}
@Composable fun NetworkCard(n:NetworkState){
    val clipboard=LocalClipboardManager.current
    val show=n.fresh||n.held
    val body="Ping ${n.ping} ms • Avg ${n.avg} ms • P95 ${n.p95} ms • Jitter ${n.jitter} ms • Loss ${n.loss}% • Quality ${n.quality}"
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("NETWORK",color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString(body))}){Text("COPY",maxLines=1)}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){NetworkMetric("Ping",if(show) "${n.ping} ms" else "—");NetworkMetric("Avg",if(show) "${n.avg} ms" else "—");NetworkMetric("P95",if(show) "${n.p95} ms" else "—");NetworkMetric("Jitter",if(show) "${n.jitter} ms" else "—");NetworkMetric("Loss",if(show) "${n.loss}%" else "—")}
        Spacer(Modifier.height(8.dp));Text("Quality: ${if(show)n.quality else "INACTIVE"}",color=when{n.fresh->Green;n.held->Amber;else->Muted},fontWeight=FontWeight.Bold)
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

@Composable fun AppRegistryListCard(repo:DjaegerRepository){
    val scope=rememberCoroutineScope()
    var appName by remember{mutableStateOf("")}
    var packageName by remember{mutableStateOf("")}
    var entries by remember{mutableStateOf<List<AppRegistryEntry>>(emptyList())}
    var status by remember{mutableStateOf("Siap. Aplikasi yang Anda tambahkan dipisahkan dari jalur game.")}
    var busy by remember{mutableStateOf(false)}
    var refreshToken by remember{mutableIntStateOf(0)}

    LaunchedEffect(refreshToken){
        busy=true
        val (ok,list)=repo.appRegistryList()
        if(ok){entries=list;if(refreshToken==0)status="Registry siap • ${list.size} aplikasi manual"}
        else status="Registry APP belum tersedia. Pastikan modul DJAEGER AI Adaptive terpasang."
        busy=false
    }

    Column(Modifier.fillMaxWidth().background(Card, RoundedCornerShape(14.dp)).padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){
        Text("APP REGISTRY • MANUAL",fontWeight=FontWeight.Bold)
        Text("Tambahkan aplikasi biasa secara manual. APP hanya diklasifikasikan dan diamati; tidak menerima game semantics, target FPS, atau aksi hardware.",color=Muted,style=MaterialTheme.typography.bodySmall)
        OutlinedTextField(value=appName,onValueChange={appName=it},label={Text("Nama aplikasi")},placeholder={Text("Contoh: Facebook")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        OutlinedTextField(value=packageName,onValueChange={packageName=it},label={Text("Package name")},placeholder={Text("com.developer.app")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={
                scope.launch{
                    busy=true
                    val (ok,msg)=repo.addManualApp(packageName,appName)
                    status=msg.replace("\n"," • ")
                    if(ok){appName="";packageName="";refreshToken++}else busy=false
                }
            },enabled=!busy&&appName.isNotBlank()&&packageName.isNotBlank(),modifier=Modifier.weight(1f)){Text(if(busy)"PROSES…" else "TAMBAH APP")}
            OutlinedButton(onClick={refreshToken++},enabled=!busy){Text("REFRESH")}
        }
        Text(status,color=if(status.contains("REJECTED")||status.contains("tidak valid")||status.contains("belum tersedia")) Red else Muted,style=MaterialTheme.typography.bodySmall)
        if(entries.isNotEmpty()){
            HorizontalDivider()
            entries.forEach{e->
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                    Column(Modifier.weight(1f)){
                        Text(e.displayName,color=AppTitleLightBlue,fontWeight=FontWeight.SemiBold)
                        Text(e.packageName,color=Muted,style=MaterialTheme.typography.bodySmall)
                        Text("MANUAL • APP_EFFICIENCY • dapat dihapus",color=Muted,style=MaterialTheme.typography.labelSmall)
                    }
                    TextButton(onClick={scope.launch{busy=true;val (ok,msg)=repo.removeManualApp(e.packageName);status=msg.replace("\n"," • ");if(ok)refreshToken++ else busy=false}},enabled=!busy){Text("HAPUS")}
                }
            }
        }
    }
}

@Composable fun GameRegistryCard(repo:DjaegerRepository){
    val scope=rememberCoroutineScope()
    var gameName by remember{mutableStateOf("")}
    var packageName by remember{mutableStateOf("")}
    var entries by remember{mutableStateOf<List<GameRegistryEntry>>(emptyList())}
    var status by remember{mutableStateOf("Siap. Game manual memakai detector DJAEGER yang sama dengan game bawaan.")}
    var busy by remember{mutableStateOf(false)}
    var refreshToken by remember{mutableIntStateOf(0)}

    LaunchedEffect(refreshToken){
        busy=true
        val (ok,list)=repo.gameRegistryList()
        if(ok){entries=list;if(refreshToken==0)status="Registry siap • ${list.count{it.type=="MANUAL"}} game manual"}
        else status="Registry belum tersedia. Pastikan modul DJAEGER AI Adaptive terpasang."
        busy=false
    }

    Column(Modifier.fillMaxWidth().background(Card, RoundedCornerShape(14.dp)).padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){
        Text("GAME REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)
        Text("Tambahkan game baru tanpa rebuild modul. Game manual masuk ke telemetry, frame learning, Gemini/Hermes review, shadow evidence, lalu executor lokal hanya bila seluruh gate keselamatan lulus.",color=Muted,style=MaterialTheme.typography.bodySmall)
        OutlinedTextField(value=gameName,onValueChange={gameName=it},label={Text("Nama game")},placeholder={Text("Contoh: Game Baru")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        OutlinedTextField(value=packageName,onValueChange={packageName=it},label={Text("Package name")},placeholder={Text("com.developer.game")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={
                scope.launch{
                    busy=true
                    val (ok,msg)=repo.addManualGame(packageName,gameName)
                    status=msg.replace("\n"," • ")
                    if(ok){gameName="";packageName="";refreshToken++}else busy=false
                }
            },enabled=!busy&&gameName.isNotBlank()&&packageName.isNotBlank(),modifier=Modifier.weight(1f)){Text(if(busy)"PROSES…" else "TAMBAH GAME")}
            OutlinedButton(onClick={refreshToken++},enabled=!busy){Text("REFRESH")}
        }
        Text(status,color=if(status.contains("REJECTED")||status.contains("tidak valid")||status.contains("belum tersedia")) Red else Muted,style=MaterialTheme.typography.bodySmall)
        if(entries.isNotEmpty()){
            HorizontalDivider()
            entries.forEach{e->
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                    Column(Modifier.weight(1f)){
                        Text(e.displayName,color=GameTitlePink,fontWeight=FontWeight.SemiBold)
                        Text(e.packageName,color=Muted,style=MaterialTheme.typography.bodySmall)
                        Text(if(e.type=="BUILTIN")"BAWAAN • terkunci" else "MANUAL • dapat dihapus",color=Muted,style=MaterialTheme.typography.labelSmall)
                    }
                    if(e.type=="MANUAL") TextButton(onClick={scope.launch{busy=true;val (ok,msg)=repo.removeManualGame(e.packageName);status=msg.replace("\n"," • ");if(ok)refreshToken++ else busy=false}},enabled=!busy){Text("HAPUS")}
                }
            }
        }
    }
}

@Composable fun Session(s:RuntimeState,samples:List<Sample>,repo:DjaegerRepository){
    val fps=samples.map{it.fps}.filter{it.isFinite()&&it>0};val frame=samples.map{it.frame}.filter{it.isFinite()&&it>0};val cpu=samples.map{it.cpu.toDouble()}.filter{it.isFinite()&&it>=0};val gpu=samples.map{it.gpu.toDouble()}.filter{it.isFinite()&&it>=0};val skin=samples.map{it.skin.toDouble()}.filter{it.isFinite()&&it>=0}
    val phase=monitorPhase(s)
    val anomalies=anomalySummary(s,samples)
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        DualRegistrySummaryCard(s)
        AppRegistryListCard(repo)
        GameRegistryCard(repo)
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
    val repo=remember{DjaegerRepository()}; var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}
    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}
    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}
    var hermesChatInput by remember{mutableStateOf("")}; var hermesChatResult by remember{mutableStateOf("Ask HERMES naturally. ONE HERMES will choose LOCAL / FAST / SMART / DEEP automatically.")}
    var authorityStatus by remember{mutableStateOf("Authority sync not loaded yet.")}
    var kernelStatus by remember{mutableStateOf("Kernel capability not loaded yet.")}
    var auditStatus by remember{mutableStateOf("Maturity audit not run yet.")}
    var recoveryStatus by remember{mutableStateOf("Recovery state not loaded yet.")}
    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}
    var comfortCommandStatus by remember{mutableStateOf("HCC1 controls ready. Current truth is read from cc_snapshot.")}
    var requestedComfortPreset by remember{mutableStateOf<String?>(null)}
    var feedbackFlash by remember{mutableStateOf<String?>(null)}
    LaunchedEffect(request){val q=request;if(q!=null){val r=repo.setUserMode(q);result=r.second;request=null}}
    LaunchedEffect(bridgeOp){
        when(bridgeOp){
            "STATUS"->{val r=repo.credentialStatus();bridgeStatus=r.second.ifBlank{"CREDENTIAL_STATUS=UNAVAILABLE"}}
            "SAVE"->{val r=repo.saveGeminiKey(keyInput);bridgeStatus=r.second;if(r.first)keyInput=""}
            "DELETE"->{val r=repo.deleteGeminiKey();bridgeStatus=r.second}
            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}
            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}
            "HERMES_CHAT"->{val r=repo.hermesChat(hermesChatInput);hermesChatResult=r.second.ifBlank{"HERMES_CHAT_ERROR=EMPTY_RESPONSE"}}
            "HERMES_CLEAR_CHAT"->{val r=repo.hermesChatClear();hermesChatResult=r.second.ifBlank{"HERMES_CHAT_HISTORY=CLEARED"}}
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
    val adaptive=s.moduleVersion.contains("adaptive",true)
    val publishedComfortPreset=hccPresetFromBlock(s.hermesHumanComfort)
    val visibleComfortPreset=requestedComfortPreset ?: publishedComfortPreset.ifBlank{if(adaptive)"LEARNED" else "COOL_STABLE"}
    LaunchedEffect(s.hermesHumanComfort,requestedComfortPreset){
        val req=requestedComfortPreset
        if(req!=null && publishedComfortPreset==req) requestedComfortPreset=null
    }
    LaunchedEffect(requestedComfortPreset){
        val req=requestedComfortPreset
        if(req!=null){delay(5000);if(requestedComfortPreset==req)requestedComfortPreset=null}
    }
    LaunchedEffect(feedbackFlash){
        val f=feedbackFlash
        if(f!=null){delay(900);if(feedbackFlash==f)feedbackFlash=null}
    }
    val supported=s.moduleVersion.contains("12.9.50"); val retained=humanDecision(s); val brainText=if(s.brain.isBlank()) "No active Local Brain state.\nLAST SESSION:\n"+retained else s.brain
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("KERNEL AUTHORITY",s.authority.ifBlank{"UNAVAILABLE — authority state not published."},true)
        BoxCard("SESSION SAFETY",(s.sessionSafety+"\n"+s.supervisor).trim().ifBlank{"UNAVAILABLE — session safety state not published."},true)
        BoxCard("GAMING TURBO MODE","Module: ${s.moduleVersion}\nConfirmed active mode: ${s.userMode}\nContract: ${if(adaptive) "ADAPTIVE AUTO • DEVICE-LEARNED" else if(supported) "DIRECT USER MODES READY" else "REQUIRES DJAEGER v12.9.21+"}\n${if(adaptive) "Static profiles are retired; AUTO follows measured device evidence." else if(result.isBlank()) "Select a mode below." else "Last command: $result"}",true)
        if(supported){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach{mode->Button(onClick={request=mode},enabled=request==null,contentPadding=PaddingValues(horizontal=7.dp,vertical=5.dp),modifier=Modifier.weight(1f)){Text(mode,style=MaterialTheme.typography.labelSmall)}}}}
        BoxCard("MODE AUTHORITY",if(adaptive) "DJAEGER AI does not use a fixed profile. Local execution is allowed only after device learning, Gemini + ONE HERMES consensus, shadow pass, thermal guard, exact OPP validation, readback, and rollback protection." else "Mode changes use only the trusted djaeger-ai mode interface. Native thermal protection remains independent and authoritative.",true)
        BoxCard("HUMAN COMFORT HCC1 CONTROL",s.hermesHumanComfort.trim().ifBlank{"HCC1 state waiting for module publication."}+"\n\nLast command: $comfortCommandStatus",true)
        if(!adaptive) Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            HccPresetButton("COOL STABLE",visibleComfortPreset=="COOL_STABLE",bridgeOp==null,{requestedComfortPreset="COOL_STABLE";bridgeOp="COMFORT_COOL"},Modifier.weight(1f))
            HccPresetButton("BASELINE",visibleComfortPreset=="BASELINE",bridgeOp==null,{requestedComfortPreset="BASELINE";bridgeOp="COMFORT_BASELINE"},Modifier.weight(1f))
            OutlinedButton(onClick={requestedComfortPreset="COOL_STABLE";bridgeOp="COMFORT_RESET"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RESET",style=MaterialTheme.typography.labelSmall)}
        }
        Text("FEEDBACK KENYAMANAN • menjadi evidence personal HCC1",color=Muted,style=MaterialTheme.typography.labelMedium)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            HccFeedbackButton("SANGAT NYAMAN",feedbackFlash=="VERY_COMFORTABLE",bridgeOp==null,{feedbackFlash="VERY_COMFORTABLE";bridgeOp="FEEDBACK_VERY_COMFORTABLE"},Modifier.weight(1f))
            HccFeedbackButton("NYAMAN",feedbackFlash=="COMFORTABLE",bridgeOp==null,{feedbackFlash="COMFORTABLE";bridgeOp="FEEDBACK_COMFORTABLE"},Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            HccFeedbackButton("KURANG NYAMAN",feedbackFlash=="LESS_COMFORTABLE",bridgeOp==null,{feedbackFlash="LESS_COMFORTABLE";bridgeOp="FEEDBACK_LESS_COMFORTABLE"},Modifier.weight(1f))
            HccFeedbackButton("TIDAK NYAMAN",feedbackFlash=="UNCOMFORTABLE",bridgeOp==null,{feedbackFlash="UNCOMFORTABLE";bridgeOp="FEEDBACK_UNCOMFORTABLE"},Modifier.weight(1f))
        }
        BoxCard("DJAEGER-AI SYNC",if(adaptive) "Target module: DJAEGER AI Adaptive v1.1.0 RC1\nTransport: verified APK↔module handshake + Gemini + ONE HERMES consensus\nControl path: observe → learn → propose → validate → shadow → local execute → readback → learn\nSYSFS execution: local gated executor only • cloud authority NONE" else "Target module: v12.9.50-r3\nTransport: Gemini v12.9.50 protected baseline\nControl path: official typed djaeger-ai commands only\nDisplay/battery cooling: not controlled by Control Center",true)
        
        
        
        
        
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="AUTHORITY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SYNC")}
            Button(onClick={bridgeOp="KERNEL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KERNEL")}
            Button(onClick={bridgeOp="AUDIT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("AUDIT")}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="RECOVERY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RECOVERY")}
            Button(onClick={bridgeOp="SNAPSHOT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SNAPSHOT")}
        }
        BoxCard("GEMINI KEY STATUS • MODULE VAULT",bridgeStatus,true)
        var vaultSlot by remember{mutableStateOf(1)}
        var vaultEpoch by remember{mutableStateOf(0)}
        var moduleVaultStatus by remember { mutableStateOf("") }
        val vaultScope=rememberCoroutineScope()
        LaunchedEffect(vaultEpoch) { val (_,runtimeVault)=repo.geminiKeyVaultStatus(); moduleVaultStatus=runtimeVault }
        BoxCard("GEMINI KEY VAULT • SINGLE SOURCE OF TRUTH",moduleVaultStatus.ifBlank{"Runtime module vault unavailable"}+"\nSelected slot: KEY $vaultSlot\nAUTO ROTATION: each key has independent cooldown; HTTP 429 rotates immediately to the next READY key.",true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){(1..4).forEach{n->OutlinedButton(onClick={vaultSlot=n},modifier=Modifier.weight(1f)){Text("KEY $n")}}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={vaultScope.launch{val r=repo.selectGeminiKey(vaultSlot.toString());moduleVaultStatus=r.second;vaultEpoch++}},modifier=Modifier.weight(1f)){Text("SET ACTIVE")}
            Button(onClick={vaultScope.launch{val r=repo.removeGeminiKey(vaultSlot.toString());moduleVaultStatus=r.second;vaultEpoch++}},modifier=Modifier.weight(1f)){Text("REMOVE SLOT")}
        }
        Text("TELEMETRI ADAPTIF 3–10 DETIK • LITTLE ${if(s.telemetry.littleKhz>=0)s.telemetry.littleKhz/1000 else 0} MHz • BIG ${if(s.telemetry.bigKhz>=0)s.telemetry.bigKhz/1000 else 0} MHz • GPU ${if(s.telemetry.gpuHz>=0)s.telemetry.gpuHz/1000000 else 0} MHz")
        OutlinedTextField(value=keyInput,onValueChange={keyInput=it},label={Text("Gemini API key")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="SAVE"},enabled=bridgeOp==null&&keyInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ADD TO MODULE VAULT")}
            Button(onClick={bridgeOp="STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}
            Button(onClick={bridgeOp="DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}
        }
        OutlinedTextField(value=chatInput,onValueChange={chatInput=it.take(8000)},label={Text("Ask DJAEGER Gemini")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="CHAT"},enabled=bridgeOp==null&&chatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK GEMINI")}
            Button(onClick={bridgeOp="CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW CHAT")}
        }
        BoxCard("GEMINI CONVERSATION",chatResult+"\n\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)
        OutlinedTextField(value=hermesChatInput,onValueChange={hermesChatInput=it.take(8000)},label={Text("Ask DJAEGER Hermes")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="HERMES_CHAT"},enabled=bridgeOp==null&&hermesChatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK HERMES")}
            Button(onClick={bridgeOp="HERMES_CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW HERMES CHAT")}
        }
        BoxCard("HERMES CONVERSATION",hermesChatResult+"\n\nONE HERMES chooses LOCAL / FAST / SMART / DEEP. Cloud failure or exhausted quota falls back to HERMES LOCAL; Gemini chat is separate.",true)
        BoxCard("AI SUMMARY LIVE",aiSummary(s));BoxCard("LOCAL BRAIN LIVE",brainText,true);BoxCard("ADAPTIVE OPERATING ENVELOPE LIVE",s.envelope.ifBlank{"No envelope published yet"},true);BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true);BoxCard("GEMINI HTTP STATE LIVE",s.geminiHttp.ifBlank{"No Gemini HTTP state yet"},true);BoxCard("GEMINI SERVER STATE LIVE",s.geminiServer.ifBlank{"No server state / no active backoff"},true)
    }
}
private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / fallback state reported";else->"State published"};return "Local brain: ${if(s.brain.isBlank())"not published" else "available"}\nEnvelope: ${if(s.envelope.isBlank())"not published" else "available"}\nGemini: $gem\nAuthority: advisory only"}
@Composable fun History(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){DecisionCard(s.latestDecision);PlanCard(s.latestPlan);BoxCard("DECISION LEDGER • LAST 16",s.decisions.ifBlank{"No decisions recorded yet"},true);BoxCard("PLAN HISTORY • LAST 16",s.plans.ifBlank{"No plans recorded yet"},true)}}
@Composable fun DecisionCard(d:DecisionRecord?){if(d==null)BoxCard("LATEST AI DECISION","No decision parsed yet") else BoxCard("LATEST AI DECISION","ID: ${d.id}\nGame: ${d.game} • Scene: ${d.scene}\nProfile: ${d.profile}\nBudgets L/B/G: ${d.little} / ${d.big} / ${d.gpu}\nOutcome: ${d.outcome}\nPred FPS/Skin: ${d.predFps} / ${d.predSkin}\nActual FPS/Skin: ${d.actualFps} / ${d.actualSkin}\nWindow: ${d.window}")}
@Composable fun PlanCard(p:PlanRecord?){if(p==null)BoxCard("LATEST PLAN","No plan parsed yet") else BoxCard("LATEST PLAN","State: ${p.state} • Score: ${p.score}\nReason: ${p.reason}\nMode/Profile: ${p.mode} / ${p.profile}\nLittle: ${p.lmin}–${p.lmax}\nBig: ${p.bmin}–${p.bmax}\nGPU: ${p.gmin}–${p.gmax}")}
@Composable fun Safety(s:RuntimeState){val stale=runtimeStateStale(s);val adaptive=envField(s.controlCenterSync,"CONTRACT")=="DJAEGER_AI_ADAPTIVE_V2";Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){WorkloadSafetyCard(s);BoxCard("MONITOR INVARIANTS","APK remains read-only\nCloud/AI never writes sysfs directly\nOnly local validated executor may write approved CPU/GPU bounds\nNo network/game traffic manipulation\nThermal guard + native thermal authority preserved");BoxCard("RUNTIME HEALTH","Root: ${if(s.root)"OK" else "UNAVAILABLE"}\nModule: ${if(s.installed)"FOUND" else "NOT FOUND"}\nController: ${if(s.controllerPid.isNotBlank())"PID ${s.controllerPid}" else "NOT REPORTED"}\nPredictor: ${if(s.predictorPid.isNotBlank())"PID ${s.predictorPid}" else "NOT REPORTED"}\nRuntime status: ${if(stale)"STALE / NOT REPORTED" else "FRESH"}\nPower telemetry: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("RESTORATION WATCH",if(adaptive)"Rollback is mandatory. The local executor restores the captured pre-apply CPU/GPU bounds whenever approval expires, workload/context changes, thermal guard closes, or readback fails." else "Control Center does not alter CPU/GPU state. Original-state restoration remains owned by DJAEGER controller lifecycle and its fail-safe paths.")}}
@Composable fun Logs(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState())){BoxCard("LIVE CONTROLLER LOG • LAST 120",s.log.ifBlank{"No controller log available"},true)}}
@Composable fun Metric(label:String,value:String,m:Modifier=Modifier){Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(value,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}
@Composable fun BoxCard(title:String,text:String,mono:Boolean=false){val clipboard=LocalClipboardManager.current;Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.labelLarge);TextButton(onClick={clipboard.setText(AnnotatedString("DJAEGER AI Adaptive v1.1.0 RC1 • VERIFIED SYNC\n["+title+"]\n"+text))}){Text("COPY",maxLines=1)}};Spacer(Modifier.height(7.dp));Text(text,color=Color(0xFFE6EAF0),fontFamily=if(mono)FontFamily.Monospace else FontFamily.Default,style=MaterialTheme.typography.bodyMedium)}}}

// CI_BASELINE_MARKER: v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC
