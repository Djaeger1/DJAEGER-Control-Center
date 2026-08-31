package com.djaeger.controlcenter

import android.os.Bundle
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
private val Bg=Color(0xFF090B10); private val Card=Color(0xFF121722); private val Green=Color(0xFF43E38A); private val Muted=Color(0xFF98A2B3); private val Amber=Color(0xFFFFC857); private val Red=Color(0xFFFF6B6B)

data class Sample(val fps:Double,val frame:Double,val cpu:Float,val gpu:Float,val skin:Float,val bat:Float)

private fun sampleTemp(value:Int)=if(value>=0)value.toFloat() else Float.NaN
private fun tempText(value:Int)=if(value>=0)"$value°C" else "—"
private fun positiveText(value:Double,suffix:String)=if(value>0)"%.1f%s".format(value,suffix) else "—"
private fun positiveLongText(value:Long,divisor:Long,suffix:String)=if(value>0)"${value/divisor}$suffix" else "—"
private fun stat3(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f / %.1f%s".format(values.average(),values.minOrNull()?:0.0,values.maxOrNull()?:0.0,unit)
private fun stat2(values:List<Double>,unit:String)=if(values.isEmpty())"—" else "%.1f / %.1f%s".format(values.average(),values.maxOrNull()?:0.0,unit)

@Composable fun App(){val repo=remember{DjaegerRepository()};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()}
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner){lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){while(true){state=repo.snapshot();if(state.root&&state.installed&&state.sampleFresh){with(state.telemetry){samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)));while(samples.size>60)samples.removeAt(0)}};delay(1000)}}}
    MaterialTheme(colorScheme=darkColorScheme(primary=Green,background=Bg,surface=Card)){Column(Modifier.fillMaxSize().background(Bg).padding(16.dp)){Text("DJAEGER",fontWeight=FontWeight.Black,style=MaterialTheme.typography.headlineMedium);Text("CONTROL CENTER • v0.12.1-r2 • DJAEGER-AI v12.9.50-r3 SYNC • REALTIME 1s",color=Muted);Spacer(Modifier.height(12.dp));ScrollableTabRow(selectedTabIndex=tab,containerColor=Bg,edgePadding=0.dp){listOf("Overview","Session","Charts","AI","History","Safety","Logs").forEachIndexed{i,n->Tab(selected=tab==i,onClick={tab=i},text={Text(n)})}};Spacer(Modifier.height(12.dp));when(tab){0->Overview(state);1->Session(state,samples);2->Charts(state,samples);3->AI(state);4->History(state);5->Safety(state);else->Logs(state)}}}}

@Composable fun Overview(s:RuntimeState){val power=if(s.telemetry.powerMw>=0)"%.1f mW".format(s.telemetry.powerMw) else "—";val current=if(s.telemetry.currentUa>0)"${s.telemetry.currentUa} µA" else "—";val voltage=if(s.telemetry.voltageUv>0)"${s.telemetry.voltageUv} µV" else "—";Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS",positiveText(s.telemetry.fps,""),Modifier.weight(1f));Metric("Frame",positiveText(s.telemetry.frameMs," ms"),Modifier.weight(1f));Metric("Jank",if(s.telemetry.jank>=0)"%.1f%%".format(s.telemetry.jank) else "—",Modifier.weight(1f))};ThermalRow(s);BoxCard("PERFORMANCE","Little: ${positiveLongText(s.telemetry.littleKhz,1000," MHz")}\nBig: ${positiveLongText(s.telemetry.bigKhz,1000," MHz")}\nGPU: ${positiveLongText(s.telemetry.gpuHz,1_000_000," MHz")}\nProfile: ${s.telemetry.profile}\nP95/P99: ${positiveText(s.telemetry.p95," ms")} / ${positiveText(s.telemetry.p99," ms")}");BoxCard("POWER","${s.telemetry.batteryStatus} • $power\n$current • $voltage\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}}
@Composable fun StatusCard(s:RuntimeState){val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;val session=when{ s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"};BoxCard("ENGINE / SESSION",if(s.installed)"${if(s.active=="1")"● ACTIVE" else "○ IDLE"} • ${if(stale)"STALE" else "LIVE"}\nModule: ${s.moduleVersion}\nGame: ${s.game}\nWindow: ${s.window}\nProfile: ${s.telemetry.profile}\nLast sample: $session\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")}
@Composable fun ThermalRow(s:RuntimeState){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Thermal("CPU",s.telemetry.cpuT,Modifier.weight(1f));Thermal("GPU",s.telemetry.gpuT,Modifier.weight(1f));Thermal("Skin",s.telemetry.skinT,Modifier.weight(1f));Thermal("Battery",s.telemetry.batT,Modifier.weight(1f))}}
@Composable fun Thermal(label:String,t:Int,m:Modifier){val c=when{t<0->Muted;t>=50->Red;t>=43->Amber;else->Green};Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(tempText(t),color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}


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
    if(s.updated>0&&now-s.updated>5)a.add("Runtime status stale (${now-s.updated}s)")
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
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString("["+title+"] "+current))}){Text("COPY")}}
        Text(current,fontWeight=FontWeight.Bold);Spacer(Modifier.height(10.dp))
        Canvas(Modifier.fillMaxWidth().height(120.dp)){if(values.size>1){val lo=min;val hi=max.coerceAtLeast(lo+1f);val step=size.width/(values.size-1);for(i in 1 until values.size){val a=values[i-1];val b=values[i];if(a.isFinite()&&b.isFinite()){val y1=size.height-(a.coerceIn(lo,hi)-lo)/(hi-lo)*size.height;val y2=size.height-(b.coerceIn(lo,hi)-lo)/(hi-lo)*size.height;drawLine(color=Green,start=Offset((i-1)*step,y1),end=Offset(i*step,y2),strokeWidth=3f)}}}}
    }}
}

@Composable fun AI(s:RuntimeState){
    val repo=remember{DjaegerRepository()}; var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}
    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}
    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}
    var authorityStatus by remember{mutableStateOf("Authority sync not loaded yet.")}
    var kernelStatus by remember{mutableStateOf("Kernel capability not loaded yet.")}
    var auditStatus by remember{mutableStateOf("Maturity audit not run yet.")}
    var recoveryStatus by remember{mutableStateOf("Recovery state not loaded yet.")}
    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}
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
        }
        bridgeOp=null
    }
    val supported=s.moduleVersion.contains("12.9.50"); val retained=humanDecision(s); val brainText=if(s.brain.isBlank()) "No active Local Brain state.\nLAST SESSION:\n"+retained else s.brain
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("GAMING TURBO MODE","Module: ${s.moduleVersion}\nConfirmed active mode: ${s.userMode}\nContract: ${if(supported) "DIRECT USER MODES READY" else "REQUIRES DJAEGER v12.9.21+"}\n${if(result.isBlank()) "Select a mode below." else "Last command: $result"}",true)
        if(supported){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach{mode->Button(onClick={request=mode},enabled=request==null,contentPadding=PaddingValues(horizontal=7.dp,vertical=5.dp),modifier=Modifier.weight(1f)){Text(mode,style=MaterialTheme.typography.labelSmall)}}}}
        BoxCard("MODE AUTHORITY","Mode changes use only the trusted djaeger-ai mode interface. Native thermal protection remains independent and authoritative.",true)
        BoxCard("DJAEGER-AI SYNC","Target module: v12.9.50-r3\nTransport: Gemini v12.9.50 protected baseline\nControl path: official typed djaeger-ai commands only\nDisplay/battery cooling: not controlled by Control Center",true)
        BoxCard("DJAEGER AI ↔ KERNEL AUTHORITY SYNC",authorityStatus,true)
        BoxCard("LIVE KERNEL CAPABILITY",kernelStatus,true)
        BoxCard("SESSION RECOVERY",recoveryStatus,true)
        BoxCard("SESSION SNAPSHOT LIFECYCLE",snapshotStatus,true)
        BoxCard("MATURITY / REGRESSION AUDIT",auditStatus,true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="AUTHORITY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SYNC")}
            Button(onClick={bridgeOp="KERNEL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KERNEL")}
            Button(onClick={bridgeOp="AUDIT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("AUDIT")}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="RECOVERY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RECOVERY")}
            Button(onClick={bridgeOp="SNAPSHOT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SNAPSHOT")}
        }
        BoxCard("GEMINI KEY STATUS",bridgeStatus,true)
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
        BoxCard("GEMINI CONVERSATION",chatResult+"\n\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)
        BoxCard("AI SUMMARY LIVE",aiSummary(s));BoxCard("LOCAL BRAIN LIVE",brainText,true);BoxCard("ADAPTIVE OPERATING ENVELOPE LIVE",s.envelope.ifBlank{"No envelope published yet"},true);BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true);BoxCard("GEMINI HTTP STATE LIVE",s.geminiHttp.ifBlank{"No Gemini HTTP state yet"},true);BoxCard("GEMINI SERVER STATE LIVE",s.geminiServer.ifBlank{"No server state / no active backoff"},true)
    }
}
private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / fallback state reported";else->"State published"};return "Local brain: ${if(s.brain.isBlank())"not published" else "available"}\nEnvelope: ${if(s.envelope.isBlank())"not published" else "available"}\nGemini: $gem\nAuthority: advisory only"}
@Composable fun History(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){DecisionCard(s.latestDecision);PlanCard(s.latestPlan);BoxCard("DECISION LEDGER • LAST 16",s.decisions.ifBlank{"No decisions recorded yet"},true);BoxCard("PLAN HISTORY • LAST 16",s.plans.ifBlank{"No plans recorded yet"},true)}}
@Composable fun DecisionCard(d:DecisionRecord?){if(d==null)BoxCard("LATEST AI DECISION","No decision parsed yet") else BoxCard("LATEST AI DECISION","ID: ${d.id}\nGame: ${d.game} • Scene: ${d.scene}\nProfile: ${d.profile}\nBudgets L/B/G: ${d.little} / ${d.big} / ${d.gpu}\nOutcome: ${d.outcome}\nPred FPS/Skin: ${d.predFps} / ${d.predSkin}\nActual FPS/Skin: ${d.actualFps} / ${d.actualSkin}\nWindow: ${d.window}")}
@Composable fun PlanCard(p:PlanRecord?){if(p==null)BoxCard("LATEST PLAN","No plan parsed yet") else BoxCard("LATEST PLAN","State: ${p.state} • Score: ${p.score}\nReason: ${p.reason}\nMode/Profile: ${p.mode} / ${p.profile}\nLittle: ${p.lmin}–${p.lmax}\nBig: ${p.bmin}–${p.bmax}\nGPU: ${p.gmin}–${p.gmax}")}
@Composable fun Safety(s:RuntimeState){val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){BoxCard("MONITOR INVARIANTS","READ-ONLY application\nNo direct sysfs writes\nNo network/game traffic manipulation\nLocal/native thermal authority preserved\nGemini remains advisory only");BoxCard("RUNTIME HEALTH","Root: ${if(s.root)"OK" else "UNAVAILABLE"}\nModule: ${if(s.installed)"FOUND" else "NOT FOUND"}\nController: ${if(s.controllerPid.isNotBlank())"PID ${s.controllerPid}" else "NOT REPORTED"}\nPredictor: ${if(s.predictorPid.isNotBlank())"PID ${s.predictorPid}" else "NOT REPORTED"}\nRuntime status: ${if(stale)"STALE / NOT REPORTED" else "FRESH"}\nPower telemetry: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("RESTORATION WATCH","Control Center does not alter CPU/GPU state. Original-state restoration remains owned by DJAEGER controller lifecycle and its fail-safe paths.")}}
@Composable fun Logs(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState())){BoxCard("LIVE CONTROLLER LOG • LAST 120",s.log.ifBlank{"No controller log available"},true)}}
@Composable fun Metric(label:String,value:String,m:Modifier=Modifier){Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(value,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}
@Composable fun BoxCard(title:String,text:String,mono:Boolean=false){val clipboard=LocalClipboardManager.current;Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.labelLarge);TextButton(onClick={clipboard.setText(AnnotatedString("DJAEGER v0.12.1-r2 • AI SYNC\n["+title+"]\n"+text))}){Text("COPY")}};Spacer(Modifier.height(7.dp));Text(text,color=Color(0xFFE6EAF0),fontFamily=if(mono)FontFamily.Monospace else FontFamily.Default,style=MaterialTheme.typography.bodyMedium)}}}

// CI_BASELINE_MARKER: v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC
