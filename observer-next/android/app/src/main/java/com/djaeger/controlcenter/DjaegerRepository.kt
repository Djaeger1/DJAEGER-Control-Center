package com.djaeger.controlcenter

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit
import java.util.concurrent.Executors

data class Telemetry(val epoch:Long=0,val cpuT:Int=-1,val gpuT:Int=-1,val skinT:Int=-1,val batT:Int=-1,val littleKhz:Long=-1,val bigKhz:Long=-1,val gpuHz:Long=-1,val profile:String="NA",val frameMs:Double=0.0,val fps:Double=0.0,val jank:Double=-1.0,val p95:Double=0.0,val p99:Double=0.0,val batteryStatus:String="NA",val currentUa:Long=-1,val voltageUv:Long=-1,val powerMw:Double=-1.0,val powerValid:String="REJECTED",val powerReason:String="NO_SAMPLE",val windowMode:String="INACTIVE")
data class DecisionRecord(val id:String,val game:String,val scene:String,val profile:String,val little:String,val big:String,val gpu:String,val predSkin:String,val predFps:String,val outcome:String,val actualSkin:String,val actualFps:String,val window:String)
data class PlanRecord(val state:String,val score:String,val reason:String,val mode:String,val profile:String,val lmin:String,val lmax:String,val bmin:String,val bmax:String,val gmin:String,val gmax:String)
data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false,val held:Boolean=false,val lastAgeSec:Long=0L)
data class GameRegistryEntry(val type:String,val packageName:String,val displayName:String)
data class AppRegistryEntry(val type:String,val packageName:String,val displayName:String)

data class StrategyTruth(val source:String="UNAVAILABLE",val proposal:String="UNAVAILABLE",val validation:String="UNAVAILABLE",val applied:String="UNAVAILABLE",val readback:String="UNAVAILABLE",val outcome:String="UNAVAILABLE",val cpuLittleMin:String="—",val cpuLittleMax:String="—",val cpuBigMin:String="—",val cpuBigMax:String="—",val gpuMin:String="—",val gpuMax:String="—",val cpuGovernor:String="—",val gpuGovernor:String="—",val powerBias:String="—",val burstLease:String="—",val comfortCeiling:String="—",val confidence:String="—",val rationale:String="Not published by current DJAEGER module",val fpsOutcome:String="—",val frameOutcome:String="—",val thermalOutcome:String="—",val powerOutcome:String="—",val learningSamples:String="—",val learningConfidence:String="—",val learningPromotion:String="—")

data class R16Plan(val epoch:String,val state:String,val score:String,val reason:String,val mode:String,val profile:String,val lmin:String,val lmax:String,val bmin:String,val bmax:String,val gmin:String,val gmax:String)
fun parseR16Plan(raw:String):R16Plan?=raw.lineSequence().map{it.trim()}.filter{it.isNotBlank()}.mapNotNull{line->val p=line.split(',');if(p.size>=12&&p[0].toLongOrNull()!=null)R16Plan(p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9],p[10],p[11])else null}.lastOrNull{it.state=="PROMOTED"}

data class RuntimeState(val root:Boolean=false,val sampleFresh:Boolean=false,val installed:Boolean=false,val active:String="0",val game:String="NA",val window:String="INACTIVE",val controllerPid:String="",val predictorPid:String="",val updated:Long=0,val userMode:String="AUTO",val moduleVersion:String="unknown",val telemetry:Telemetry=Telemetry(),val brain:String="",val thoughts:String="",val memoryStatus:String="",val strategyResult:String="",val execution:String="",val authority:String="",val sessionSafety:String="",val supervisor:String="",val hermesCtx1Status:String="",val hermesCtx1Runtime:String="",val hermesCtx1Safety:String="",val hermesCtx1Hardware:String="",val hermesCtx1Memory:String="",val hermesCtx1Learning:String="",val hermesCognitionStatus:String="",val hermesMemoryVNext:String="",val hermesReasoningV2:String="",val hermesSkillsVNext:String="",val hermesLearningV2:String="",val hermesResearchV2:String="",val hermesHumanComfort:String="",val hermesLanguage:String="",val hermesMath:String="",val hermesKernel1:String="",val agentSysfs1Capability:String="",val agentSysfs1Execution:String="",val controlCenterSync:String="",val workloadContext:String="",val workloadGate:String="",val proposalBinding:String="",val workloadFinal:String="",val workloadExecGuard:String="",val appRegistry:String="",val gameRegistryManual:String="",val envelope:String="",val geminiHttp:String="",val geminiServer:String="",val decisions:String="",val plans:String="",val frameIntel:String="",val log:String="",val latestDecision:DecisionRecord?=null,val latestPlan:PlanRecord?=null,val error:String="",val network:NetworkState=NetworkState(),val bugHealth:BugHealthState=BugHealthState(),val strategy:StrategyTruth=StrategyTruth())

class DjaegerRepository {
    private var lastGoodNetwork:NetworkState?=null
    private var lastGoodNetworkAt:Long=0L
    private val module="/data/adb/modules/djaeger_ai_observer"; private val persistent="/data/adb/djaeger_observer"
    private val apkVersionCode=104
    private val syncSchema="DJAEGER_AI_ADAPTIVE_V2"
    private fun su(command:String,timeoutMs:Long=2500):Pair<Int,String> {
        val readerExecutor=Executors.newSingleThreadExecutor()
        return try {
            val p=ProcessBuilder("su","-c",command).redirectErrorStream(true).start()
            val outputFuture=readerExecutor.submit<String> { p.inputStream.bufferedReader().use { it.readText() } }
            if(!p.waitFor(timeoutMs,TimeUnit.MILLISECONDS)){
                p.destroy(); if(p.isAlive)p.destroyForcibly()
                outputFuture.cancel(true)
                Pair(-2,"Root request timed out after ${timeoutMs}ms")
            } else {
                val output=try{ outputFuture.get(300,TimeUnit.MILLISECONDS) }catch(_:Exception){ "" }
                Pair(p.exitValue(),output)
            }
        } catch(e:Exception){ Pair(-1,e.message?:"root execution failed") }
        finally { readerExecutor.shutdownNow() }
    }
    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){
        val read = ConsolidatedSnapshotReader(persistent + "/cc_snapshot").read(4000)
        val mapped = ConsolidatedRuntimeMapper.map(read)
            ?: return@withContext RuntimeState(error=read.error.ifBlank { "SNAPSHOT_UNAVAILABLE" })

        val rt = mapped.runtime
        val tel = parseTelemetry(mapped.telemetryRaw)
        val now = System.currentTimeMillis()/1000
        val age = if(tel.epoch > 0) now - tel.epoch else Long.MAX_VALUE
        val adaptiveContract = AtomicSnapshot.keyValues(mapped.controlCenterSync)["CONTRACT"] == syncSchema
        val telemetryTtlSec = if(adaptiveContract) 15L else 5L
        val fresh = tel.epoch > 0 && age in 0..telemetryTtlSec
        val runtimeUpdated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0L
        val activeClaim=(rt["ACTIVE"] ?: rt["active"] ?: "0") == "1"
        val runtimeTtlSec=15L
        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec
        // SYNC2: ACTIVE/GAME/WINDOW are session truth from atomic runtime.
        // Telemetry/frame staleness may mark metrics stale, never demote a live session.
        val sessionFresh=runtimeFresh

        // Preserve r7 Network Intelligence while keeping r9's single atomic read.
        // NETWORK is already published by DJAEGER inside cc_snapshot; no network
        // commands, sysfs reads, or game traffic changes are performed here.
        val nkv = AtomicSnapshot.keyValues(mapped.network)
        val netAt = nkv["UPDATED_AT"]?.toLongOrNull() ?: 0L
        val netFresh = nkv["SESSION_ACTIVE"] == "1" && netAt > 0 && (now-netAt) in 0..30
        val liveNetwork = if(netFresh) NetworkState(
            ping=nkv["PING_CURRENT_MS"] ?: "—",
            avg=nkv["PING_AVG_MS"] ?: "—",
            p95=nkv["PING_P95_MS"] ?: "—",
            jitter=nkv["JITTER_MS"] ?: "—",
            loss=nkv["PACKET_LOSS_PCT"] ?: "—",
            quality=nkv["QUALITY"] ?: "UNKNOWN",
            fresh=true,
            held=false,
            lastAgeSec=0L
        ) else null
        if(liveNetwork!=null){lastGoodNetwork=liveNetwork;lastGoodNetworkAt=now}
        val runtimeSessionActive=(rt["ACTIVE"] ?: rt["active"] ?: "0")=="1"
        val holdAge=if(lastGoodNetworkAt>0L) now-lastGoodNetworkAt else Long.MAX_VALUE
        val network=when{
            liveNetwork!=null -> liveNetwork
            runtimeSessionActive && lastGoodNetwork!=null && holdAge in 1L..10L -> lastGoodNetwork!!.copy(
                fresh=false,
                held=true,
                lastAgeSec=holdAge,
                quality="${lastGoodNetwork!!.quality} • HOLD ${holdAge}s"
            )
            else -> NetworkState()
        }

        fun rv(vararg k:String):String{k.forEach{if(!rt[it].isNullOrBlank())return rt[it]!!};return "—"}
        val plan= parseR16Plan(mapped.plans)
        val dec = parseDecision(mapped.decisions)
        val frameLine=mapped.frameIntel.lineSequence().filter{it.isNotBlank()}.lastOrNull().orEmpty().split(',')
        val frameEpoch=frameLine.getOrNull(0)?.toLongOrNull()?:0L
        val frameFresh=frameEpoch>0 && (now-frameEpoch) in 0..15
        val frameParts=mapped.frameIntel.lineSequence().filter{it.isNotBlank()}.lastOrNull().orEmpty().split(',')
        val fEpoch=frameParts.getOrNull(0)?.toLongOrNull()?:0L
        val fFresh=fEpoch>0 && (now-fEpoch) in 0..15
        val telBound=if(activeClaim && runtimeFresh && fFresh) tel.copy(epoch=fEpoch,profile=frameParts.getOrNull(1)?:tel.profile,frameMs=frameParts.getOrNull(2)?.toDoubleOrNull()?:tel.frameMs,fps=frameParts.getOrNull(3)?.toDoubleOrNull()?:tel.fps,jank=frameParts.getOrNull(4)?.toDoubleOrNull()?:tel.jank,p95=frameParts.getOrNull(5)?.toDoubleOrNull()?:tel.p95,p99=frameParts.getOrNull(6)?.toDoubleOrNull()?:tel.p99) else tel
        val execKv=AtomicSnapshot.keyValues(mapped.execution)
        val strategy=StrategyTruth(
            source=rv("DECISION_SOURCE","decision_source","SOURCE").let{if(it=="—") rv("SOURCE") else it},
            proposal=plan?.let{"LAST PROPOSAL @${it.epoch}: ${it.mode} ${it.profile}"}?:"UNAVAILABLE",
            validation=plan?.let{"${it.state} score=${it.score}: ${it.reason}"}?:"UNAVAILABLE",
            applied=execKv["STATUS"] ?: "IDLE",
            readback=execKv["READBACK"] ?: "UNAVAILABLE",
            outcome=dec?.outcome?:"UNAVAILABLE",
            cpuLittleMin=plan?.lmin?:"—",cpuLittleMax=plan?.lmax?:"—",cpuBigMin=plan?.bmin?:"—",cpuBigMax=plan?.bmax?:"—",gpuMin=plan?.gmin?:"—",gpuMax=plan?.gmax?:"—",
            confidence=plan?.score?:rv("STRATEGY_CONFIDENCE","CONFIDENCE"),
            rationale=plan?.reason?:rv("STRATEGY_RATIONALE","RATIONALE"),
            fpsOutcome=if(frameFresh) frameLine.getOrNull(3)?:"—" else dec?.actualFps?:"—",
            frameOutcome=if(frameFresh) frameLine.getOrNull(2)?:"—" else "—",
            thermalOutcome=dec?.actualSkin?:"—",powerOutcome=if(tel.powerValid=="VALID") "${tel.powerMw} mW" else "—",
            learningSamples=rv("LEARNING_SAMPLES","SAMPLES"),learningConfidence=rv("LEARNING_CONFIDENCE","CONFIDENCE"),learningPromotion=rv("LEARNED_STATE","LEARNING_STATUS"))

        RuntimeState(
            root=true,
            sampleFresh=fresh,
            installed=mapped.installed,
            active=if(sessionFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",
            game=if(sessionFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",
            window=if(sessionFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",
            controllerPid=rt["CONTROLLER_PID"] ?: rt["controller_pid"] ?: "",
            predictorPid=rt["PREDICTOR_PID"] ?: rt["predictor_pid"] ?: "",
            updated=(rt["UPDATED_AT"] ?: rt["updated_at"])?.toLongOrNull() ?: 0,
            userMode=rt["USER_MODE"] ?: rt["user_mode"] ?: "AUTO",
            moduleVersion=mapped.moduleVersion,
            telemetry=telBound,
            brain=mapped.brain,
            thoughts=mapped.thoughts,
            memoryStatus=mapped.memoryStatus,strategyResult=mapped.strategyResult,execution=mapped.execution,authority=mapped.authority,sessionSafety=mapped.sessionSafety,supervisor=mapped.supervisor,hermesCtx1Status=mapped.hermesCtx1Status,hermesCtx1Runtime=mapped.hermesCtx1Runtime,hermesCtx1Safety=mapped.hermesCtx1Safety,hermesCtx1Hardware=mapped.hermesCtx1Hardware,hermesCtx1Memory=mapped.hermesCtx1Memory,hermesCtx1Learning=mapped.hermesCtx1Learning,hermesCognitionStatus=mapped.hermesCognitionStatus,hermesMemoryVNext=mapped.hermesMemoryVNext,hermesReasoningV2=mapped.hermesReasoningV2,hermesSkillsVNext=mapped.hermesSkillsVNext,hermesLearningV2=mapped.hermesLearningV2,hermesResearchV2=mapped.hermesResearchV2,hermesHumanComfort=mapped.hermesHumanComfort,hermesLanguage=mapped.hermesLanguage,hermesMath=mapped.hermesMath,hermesKernel1=mapped.hermesKernel1,agentSysfs1Capability=mapped.agentSysfs1Capability,agentSysfs1Execution=mapped.agentSysfs1Execution,controlCenterSync=mapped.controlCenterSync,workloadContext=mapped.workloadContext,workloadGate=mapped.workloadGate,proposalBinding=mapped.proposalBinding,workloadFinal=mapped.workloadFinal,workloadExecGuard=mapped.workloadExecGuard,appRegistry=mapped.appRegistry,gameRegistryManual=mapped.gameRegistryManual,
            envelope=mapped.envelope,
            geminiHttp=mapped.geminiHttp,
            geminiServer=mapped.geminiServer,
            decisions=mapped.decisions,
            plans=mapped.plans,
            frameIntel=mapped.frameIntel,
            log=mapped.log,
            latestDecision=parseDecision(mapped.decisions),
            latestPlan=parsePlan(mapped.plans),
            network=network,
            bugHealth=mapped.bugHealth,
            strategy=strategy
        )
    }

    suspend fun synchronizeLocal():Pair<Boolean,String> = withContext(Dispatchers.IO) {
        val requestId="cc-"+System.currentTimeMillis().toString()
        val (rc,out)=su("$module/bin/observerctl.sh sync-request $apkVersionCode $syncSchema $requestId",7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"SYNC_STATUS=EMPTY_ACK" else "SYNC_STATUS=FAILED"})
    }

    suspend fun credentialStatus():Pair<Boolean,String> = withContext(Dispatchers.IO) {
        val (rc,out)=su("$module/bin/observerctl.sh credential-status",5000)
        Pair(rc==0,out.trim().ifBlank{"CREDENTIAL_STATUS=UNAVAILABLE"})
    }

    suspend fun setUserMode(mode:String):Pair<Boolean,String> = withContext(Dispatchers.IO) {
        when(mode.uppercase()){
            "AUTO" -> { val (rc,out)=su("$module/bin/observerctl.sh execution-auto",5000); Pair(rc==0,out.trim()) }
            "OFF" -> { val (rc,out)=su("$module/bin/observerctl.sh execution-off",5000); Pair(rc==0,out.trim()) }
            else -> Pair(false,"ADAPTIVE_ONLY • static profiles are retired")
        }
    }

    suspend fun setHumanComfortPreset(preset:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        Pair(false,"ADAPTIVE_ONLY • comfort input is learned as evidence, not a fixed preset")
    }

    suspend fun submitHumanComfortFeedback(level:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val arg=when(level.uppercase()){
            "VERY_COMFORTABLE"->"very-comfortable"
            "COMFORTABLE"->"comfortable"
            "LESS_COMFORTABLE"->"less-comfortable"
            "UNCOMFORTABLE"->"uncomfortable"
            else->return@withContext Pair(false,"INVALID_COMFORT_FEEDBACK")
        }
        val (rc,out)=su("$module/bin/observerctl.sh feedback $arg",5000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"COMFORT_FEEDBACK_RECORDED" else "COMFORT_FEEDBACK_FAILED"})
    }

    private fun suStdin(command:String,input:String,timeoutMs:Long=30000):Pair<Int,String>{
        val readerExecutor=Executors.newSingleThreadExecutor()
        return try{
            val p=ProcessBuilder("su","-c",command).redirectErrorStream(true).start()
            val outputFuture=readerExecutor.submit<String>{p.inputStream.bufferedReader().use{it.readText()}}
            p.outputStream.bufferedWriter().use{w->w.write(input);w.newLine();w.flush()}
            if(!p.waitFor(timeoutMs,TimeUnit.MILLISECONDS)){
                p.destroy();if(p.isAlive)p.destroyForcibly();outputFuture.cancel(true)
                Pair(-2,"BRIDGE_TIMEOUT=${timeoutMs}ms")
            }else{
                val out=try{outputFuture.get(500,TimeUnit.MILLISECONDS)}catch(_:Exception){""}
                Pair(p.exitValue(),out)
            }
        }catch(e:Exception){Pair(127,"BRIDGE_ERROR="+(e.message?:"unknown"))}
        finally{readerExecutor.shutdownNow()}
    }
    suspend fun geminiKeyStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh gemini-key-status",5000); Pair(rc==0,out.trim())
    }
    suspend fun saveGeminiKey(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(key.isBlank()) return@withContext Pair(false,"KEY_REJECTED=EMPTY")
        val (rc,out)=suStdin("$module/bin/observerctl.sh gemini-key-stdin",key); Pair(rc==0,out.trim())
    }
    suspend fun deleteGeminiKey():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh gemini-key-delete",5000); Pair(rc==0,out.trim())
    }
    suspend fun geminiKeyVaultStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh gemini-key-vault-status",5000); Pair(rc==0,out.trim())
    }
    suspend fun addGeminiKeyToVault(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(key.isBlank()) return@withContext Pair(false,"KEY_REJECTED=EMPTY")
        val (rc,out)=suStdin("$module/bin/observerctl.sh gemini-key-add-stdin",key); Pair(rc==0,out.trim())
    }
    suspend fun selectGeminiKey(index:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(index.toIntOrNull()==null) return@withContext Pair(false,"KEY_SELECT_REJECTED=INDEX")
        val (rc,out)=su("$module/bin/observerctl.sh gemini-key-select $index",5000); Pair(rc==0,out.trim())
    }
    suspend fun removeGeminiKey(index:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(index.toIntOrNull()==null) return@withContext Pair(false,"KEY_REMOVE_REJECTED=INDEX")
        val (rc,out)=su("$module/bin/observerctl.sh gemini-key-remove $index",5000); Pair(rc==0,out.trim())
    }

    suspend fun geminiChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(prompt.isBlank()) return@withContext Pair(false,"CHAT_ERROR=EMPTY_PROMPT")
        val (rc,out)=suStdin("$module/bin/observerctl.sh gemini-chat-stdin",prompt.take(8000)); Pair(rc==0,out.trim())
    }

    suspend fun geminiKnowledgeStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh gemini-knowledge-status"); Pair(rc==0,out.trim())
    }
    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh gemini-chat-clear",5000); Pair(rc==0,out.trim())
    }

    suspend fun hermesChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(prompt.isBlank()) return@withContext Pair(false,"HERMES_CHAT_ERROR=EMPTY_PROMPT")
        val (rc,out)=suStdin("$module/bin/observerctl.sh hermes-chat-stdin",prompt.take(8000),40000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_ERROR=EMPTY_RESPONSE" else "HERMES_CHAT_FAILED"})
    }

    suspend fun hermesChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh hermes-chat-clear",5000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"HERMES_CHAT_HISTORY=CLEARED" else "HERMES_CHAT_CLEAR_FAILED"})
    }

    suspend fun authoritySyncStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh authority-status",10000); Pair(rc==0,out.trim())
    }
    suspend fun kernelCapabilitySummary():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh kernel-status",10000); Pair(rc==0,out.trim())
    }
    suspend fun maturityAudit():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh maturity-audit",30000); Pair(rc==0,out.trim())
    }
    suspend fun recoveryStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh migration-status",10000); Pair(rc==0,out.trim())
    }
    suspend fun snapshotLifecycleStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh snapshot-status",10000); Pair(rc==0,out.trim())
    }


    suspend fun gameRegistryList():Pair<Boolean,List<GameRegistryEntry>> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh game-registry-list",5000)
        if(rc!=0) return@withContext Pair(false,emptyList())
        val rows=out.lineSequence().mapNotNull{line->
            val p=line.split('|',limit=3)
            if(p.size==3&&(p[0]=="BUILTIN"||p[0]=="MANUAL")&&p[1].isNotBlank()) GameRegistryEntry(p[0],p[1],p[2].ifBlank{p[1]}) else null
        }.toList()
        Pair(true,rows)
    }

    suspend fun addManualGame(packageName:String,displayName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        val name=displayName.replace('\n',' ').replace('\r',' ').replace('\t',' ').trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        if(name.isBlank()||name.toByteArray().size>120) return@withContext Pair(false,"Nama game kosong atau terlalu panjang")
        val (rc,out)=suStdin("$module/bin/observerctl.sh game-registry-add-stdin",pkg+"\n"+name,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=ADDED" else "STATUS=FAILED"})
    }

    suspend fun removeManualGame(packageName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        val (rc,out)=suStdin("$module/bin/observerctl.sh game-registry-remove-stdin",pkg,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=REMOVED" else "STATUS=FAILED"})
    }


    suspend fun appRegistryList():Pair<Boolean,List<AppRegistryEntry>> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/bin/observerctl.sh app-registry-list",5000)
        if(rc!=0) return@withContext Pair(false,emptyList())
        val rows=out.lineSequence().mapNotNull{line->
            val p=line.split('|',limit=3)
            if(p.size==3&&p[0]=="MANUAL"&&p[1].isNotBlank()) AppRegistryEntry(p[0],p[1],p[2].ifBlank{p[1]}) else null
        }.toList()
        Pair(true,rows)
    }

    suspend fun addManualApp(packageName:String,displayName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        val name=displayName.replace('\n',' ').replace('\r',' ').replace('\t',' ').trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        if(name.isBlank()||name.toByteArray().size>120) return@withContext Pair(false,"Nama aplikasi kosong atau terlalu panjang")
        val (rc,out)=suStdin("$module/bin/observerctl.sh app-registry-add-stdin",pkg+"\n"+name,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=ADDED" else "STATUS=FAILED"})
    }

    suspend fun removeManualApp(packageName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        val (rc,out)=suStdin("$module/bin/observerctl.sh app-registry-remove-stdin",pkg,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=REMOVED" else "STATUS=FAILED"})
    }

    private fun parseTelemetry(line: String): Telemetry {
    val c = parseCsv(line)
    fun field(i: Int): String = c.getOrNull(i)?.trim().orEmpty()
    return Telemetry(field(0).toLongOrNull()?:0,field(1).toIntOrNull()?:-1,field(2).toIntOrNull()?:-1,field(3).toIntOrNull()?:-1,field(4).toIntOrNull()?:-1,field(5).toLongOrNull()?:-1,field(6).toLongOrNull()?:-1,field(7).toLongOrNull()?:-1,field(8),field(9).toDoubleOrNull()?:0.0,field(10).toDoubleOrNull()?:0.0,field(11).toDoubleOrNull()?:-1.0,field(12).toDoubleOrNull()?:0.0,field(13).toDoubleOrNull()?:0.0,field(15),field(16).toLongOrNull()?:0,field(17).toLongOrNull()?:0,field(18).toDoubleOrNull()?:0.0,field(19),field(20),field(22))
}
    private fun parseDecision(text:String):DecisionRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("decision_id,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<16)return null;return DecisionRecord(c[0],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11],c[12],c[15])}
    private fun parsePlan(text:String):PlanRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("epoch,")&&!it.startsWith("state,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<12)return null;return PlanRecord(c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11])}
    private fun parseCsv(line:String):List<String>{val out=mutableListOf<String>();val cur=StringBuilder();var q=false;var i=0;while(i<line.length){val ch=line[i];if(ch=='"'){if(q&&i+1<line.length&&line[i+1]=='"'){cur.append('"');i++}else q=!q}else if(ch==','&&!q){out.add(cur.toString());cur.setLength(0)}else cur.append(ch);i++};out.add(cur.toString());return out}
}
