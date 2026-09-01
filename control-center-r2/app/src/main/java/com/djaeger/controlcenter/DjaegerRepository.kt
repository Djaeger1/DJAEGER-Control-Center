package com.djaeger.controlcenter

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit
import java.util.concurrent.Executors

data class Telemetry(val epoch:Long=0,val cpuT:Int=-1,val gpuT:Int=-1,val skinT:Int=-1,val batT:Int=-1,val littleKhz:Long=-1,val bigKhz:Long=-1,val gpuHz:Long=-1,val profile:String="NA",val frameMs:Double=0.0,val fps:Double=0.0,val jank:Double=0.0,val p95:Double=0.0,val p99:Double=0.0,val batteryStatus:String="NA",val currentUa:Long=-1,val voltageUv:Long=-1,val powerMw:Double=-1.0,val powerValid:String="REJECTED",val powerReason:String="NO_SAMPLE",val windowMode:String="INACTIVE")
data class DecisionRecord(val id:String,val game:String,val scene:String,val profile:String,val little:String,val big:String,val gpu:String,val predSkin:String,val predFps:String,val outcome:String,val actualSkin:String,val actualFps:String,val window:String)
data class PlanRecord(val state:String,val score:String,val reason:String,val mode:String,val profile:String,val lmin:String,val lmax:String,val bmin:String,val bmax:String,val gmin:String,val gmax:String)
data class RuntimeState(val root:Boolean=false,val sampleFresh:Boolean=false,val installed:Boolean=false,val active:String="0",val game:String="NA",val window:String="INACTIVE",val controllerPid:String="",val predictorPid:String="",val updated:Long=0,val userMode:String="AUTO",val moduleVersion:String="unknown",val telemetry:Telemetry=Telemetry(),val brain:String="",val envelope:String="",val geminiHttp:String="",val geminiServer:String="",val decisions:String="",val plans:String="",val frameIntel:String="",val log:String="",val latestDecision:DecisionRecord?=null,val latestPlan:PlanRecord?=null,val error:String="")

class DjaegerRepository {
    private val module="/data/adb/modules/djaeger_game_stabilizer"; private val persistent="/data/adb/djaeger_ai"
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
        val dollar = '$'
        val liveCmd = """
        echo __INSTALLED__; [ -d '$module' ] && echo 1 || echo 0
        echo __VERSION__; sed -n 's/^version=//p' '$module/module.prop' 2>/dev/null | head -n 1
        echo __RUNTIME__; cat '$persistent/runtime_status' 2>/dev/null
        echo __TEL__; tail -n 1 '$module/telemetry.csv' 2>/dev/null
        echo __LIVE__
        printf 'LITTLE_KHZ='; cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq 2>/dev/null || true; printf '\n'
        printf 'BIG_KHZ='; cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq 2>/dev/null || true; printf '\n'
        printf 'GPU_HZ='; cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null || true; printf '\n'
        printf 'BAT_TEMP_RAW='; cat /sys/class/power_supply/battery/temp 2>/dev/null || true; printf '\n'
        printf 'BAT_STATUS='; cat /sys/class/power_supply/battery/status 2>/dev/null || true; printf '\n'
        printf 'BAT_VOLTAGE_UV='; cat /sys/class/power_supply/battery/voltage_now 2>/dev/null || true; printf '\n'
        printf 'BAT_CURRENT_A='; cat /sys/class/power_supply/battery/current_now 2>/dev/null || true; printf '\n'
        printf 'BAT_CURRENT_B='; cat /sys/class/power_supply/sm5602_bat/current_now 2>/dev/null || true; printf '\n'
        for z in /sys/class/thermal/thermal_zone*; do [ -r "${dollar}z/type" ] && [ -r "${dollar}z/temp" ] || continue; n=$dollar(cat "${dollar}z/type" 2>/dev/null); t=$dollar(cat "${dollar}z/temp" 2>/dev/null); printf 'THERMAL=%s|%s\n' "${dollar}n" "${dollar}t"; done
        echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null
        echo __ENV__; cat '$persistent/adaptive_operating_envelope' 2>/dev/null
        echo __HTTP__; cat '$persistent/gemini_http_state' 2>/dev/null
        echo __SERVER__; cat '$persistent/gemini_server_state' 2>/dev/null
        echo __DECISIONS__; tail -n 16 '$persistent/decision_ledger.csv' 2>/dev/null
        echo __PLANS__; tail -n 16 '$persistent/plan_history.csv' 2>/dev/null
        echo __FRAME__; tail -n 30 '$module/frame_intel.csv' 2>/dev/null
        echo __LOG__; tail -n 120 '$module/controller.log' 2>/dev/null
        """.trimIndent()
        val (rc,out)=su(liveCmd)
        if(rc!=0)return@withContext RuntimeState(error=out.ifBlank{"Root permission unavailable"})
        fun section(a:String,b:String?):String{val x=out.substringAfter("__${a}__\n","");return if(b==null)x else x.substringBefore("__${b}__\n","")}
        val installed=section("INSTALLED","VERSION").trim()=="1"
        val moduleVersion=section("VERSION","RUNTIME").trim().ifBlank{"unknown"}
        val rt=section("RUNTIME","TEL").lineSequence().mapNotNull{line->
            val p=line.indexOf('='); if(p<=0)null else line.substring(0,p).trim() to line.substring(p+1).trim()
        }.toMap()
        val csv=parseTelemetry(section("TEL","LIVE").trim())
        val live=mutableMapOf<String,String>()
        val thermals=mutableListOf<Pair<String,Double>>()
        section("LIVE","BRAIN").lineSequence().forEach{line->
            if(line.startsWith("THERMAL=")){
                val q=line.removePrefix("THERMAL=").split('|',limit=2)
                if(q.size==2){val raw=q[1].trim().toDoubleOrNull();if(raw!=null){val c=if(kotlin.math.abs(raw)>1000.0)raw/1000.0 else raw;thermals.add(q[0].trim() to c)}}
            }else{
                val p=line.indexOf('=');if(p>0)live[line.substring(0,p).trim()]=line.substring(p+1).trim()
            }
        }
        fun maxTemp(test:(String)->Boolean):Int=TelemetryNormalizer.maxThermal(thermals,test)
        val cpuLive=maxTemp{it.matches(Regex("^(cpu|cpuss)-.*",RegexOption.IGNORE_CASE))}
        val gpuLive=maxTemp{it.matches(Regex("^gpuss-.*",RegexOption.IGNORE_CASE))}
        val skinLive=maxTemp{it.contains("skin",ignoreCase=true)}
        val br=live["BAT_TEMP_RAW"]?.toDoubleOrNull()
        val batLive=TelemetryNormalizer.normalizeBatteryTemp(br)
        fun pos(key:String):Long?=live[key]?.toLongOrNull()?.takeIf{it>0}
        val little=pos("LITTLE_KHZ")?:csv.littleKhz
        val big=pos("BIG_KHZ")?:csv.bigKhz
        val gpu=pos("GPU_HZ")?:csv.gpuHz
        val ca=live["BAT_CURRENT_A"]?.toLongOrNull()
        val cb=live["BAT_CURRENT_B"]?.toLongOrNull()
        val voltageLive=pos("BAT_VOLTAGE_UV")
        val statusLive=live["BAT_STATUS"]?.takeIf{it.isNotBlank()}
        val powerLive=TelemetryNormalizer.observePower(ca,cb,voltageLive,statusLive)
        val hasLivePower=ca!=null||cb!=null||voltageLive!=null||statusLive!=null
        val tel=csv.copy(
            cpuT=if(cpuLive>=0)cpuLive else csv.cpuT,
            gpuT=if(gpuLive>=0)gpuLive else csv.gpuT,
            skinT=if(skinLive>=0)skinLive else csv.skinT,
            batT=if(batLive>=0)batLive else csv.batT,
            littleKhz=little,bigKhz=big,gpuHz=gpu,
            batteryStatus=statusLive?:csv.batteryStatus,
            currentUa=if(hasLivePower)powerLive.currentUa else csv.currentUa,
            voltageUv=if(hasLivePower)powerLive.voltageUv else csv.voltageUv,
            powerMw=if(hasLivePower)powerLive.powerMw else csv.powerMw,
            powerValid=if(hasLivePower)powerLive.valid else csv.powerValid,
            powerReason=if(hasLivePower)powerLive.reason else csv.powerReason
        )
        val now=System.currentTimeMillis()/1000;val age=now-tel.epoch
        val decisions=section("DECISIONS","PLANS").trim();val plans=section("PLANS","FRAME").trim()
        val liveFresh=cpuLive>=0||gpuLive>=0||skinLive>=0||batLive>=0||little>0||big>0||gpu>0||hasLivePower
        val csvFresh=tel.epoch>0&&age in 0..5
        RuntimeState(root=true,sampleFresh=liveFresh||csvFresh,installed=installed,active=rt["active"]?:"0",game=rt["game"]?:"NA",window=rt["window_mode"]?:"INACTIVE",controllerPid=rt["controller_pid"]?:"",predictorPid=rt["predictor_pid"]?:"",updated=rt["updated_at"]?.toLongOrNull()?:0,userMode=rt["user_mode"]?:"AUTO",moduleVersion=moduleVersion,telemetry=tel,brain=section("BRAIN","ENV").trim(),envelope=section("ENV","HTTP").trim(),geminiHttp=section("HTTP","SERVER").trim(),geminiServer=section("SERVER","DECISIONS").trim(),decisions=decisions,plans=plans,frameIntel=section("FRAME","LOG").trim(),log=section("LOG",null).trim(),latestDecision=parseDecision(decisions),latestPlan=parsePlan(plans))
    }

    suspend fun setUserMode(mode:String):Pair<Boolean,String> = withContext(Dispatchers.IO) {
        val normalized=mode.uppercase()
        val arg=when(normalized){"AUTO"->"auto";"DINGIN"->"dingin";"SEDANG"->"sedang";"HANGAT"->"hangat";"PANAS"->"panas";else->return@withContext Pair(false,"INVALID_MODE")}
        val (rc,out)=su("djaeger-ai mode $arg")
        Pair(rc==0,out.trim().ifBlank{if(rc==0) "REQUEST_SENT" else "MODE_COMMAND_FAILED"})
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
        val (rc,out)=su("djaeger-ai gemini-key-status",5000); Pair(rc==0,out.trim())
    }
    suspend fun saveGeminiKey(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(key.isBlank()) return@withContext Pair(false,"KEY_REJECTED=EMPTY")
        val (rc,out)=suStdin("djaeger-ai gemini-key-stdin",key); Pair(rc==0,out.trim())
    }
    suspend fun deleteGeminiKey():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-key-delete",5000); Pair(rc==0,out.trim())
    }
    suspend fun geminiKeyVaultStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-key-vault-status",5000); Pair(rc==0,out.trim())
    }
    suspend fun addGeminiKeyToVault(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(key.isBlank()) return@withContext Pair(false,"KEY_REJECTED=EMPTY")
        val (rc,out)=suStdin("djaeger-ai gemini-key-add-stdin",key); Pair(rc==0,out.trim())
    }
    suspend fun selectGeminiKey(index:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(index.toIntOrNull()==null) return@withContext Pair(false,"KEY_SELECT_REJECTED=INDEX")
        val (rc,out)=su("djaeger-ai gemini-key-select $index",5000); Pair(rc==0,out.trim())
    }
    suspend fun removeGeminiKey(index:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(index.toIntOrNull()==null) return@withContext Pair(false,"KEY_REMOVE_REJECTED=INDEX")
        val (rc,out)=su("djaeger-ai gemini-key-remove $index",5000); Pair(rc==0,out.trim())
    }

    suspend fun geminiChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(prompt.isBlank()) return@withContext Pair(false,"CHAT_ERROR=EMPTY_PROMPT")
        val (rc,out)=suStdin("djaeger-ai gemini-chat-stdin",prompt.take(8000)); Pair(rc==0,out.trim())
    }

    suspend fun geminiKnowledgeStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-knowledge-status"); Pair(rc==0,out.trim())
    }
    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-chat-clear",5000); Pair(rc==0,out.trim())
    }

    suspend fun authoritySyncStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai authority-sync status",10000); Pair(rc==0,out.trim())
    }
    suspend fun kernelCapabilitySummary():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai kernel-capability-summary",10000); Pair(rc==0,out.trim())
    }
    suspend fun maturityAudit():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai maturity-audit",30000); Pair(rc==0,out.trim())
    }
    suspend fun recoveryStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai session-recovery-status",10000); Pair(rc==0,out.trim())
    }
    suspend fun snapshotLifecycleStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai snapshot-lifecycle-status",10000); Pair(rc==0,out.trim())
    }

    private fun parseTelemetry(line: String): Telemetry {
    val c = parseCsv(line)
    fun field(i: Int): String = c.getOrNull(i)?.trim().orEmpty()
    return Telemetry(field(0).toLongOrNull()?:0,field(1).toIntOrNull()?:-1,field(2).toIntOrNull()?:-1,field(3).toIntOrNull()?:-1,field(4).toIntOrNull()?:-1,field(5).toLongOrNull()?:-1,field(6).toLongOrNull()?:-1,field(7).toLongOrNull()?:-1,field(8),field(9).toDoubleOrNull()?:0.0,field(10).toDoubleOrNull()?:0.0,field(11).toDoubleOrNull()?:0.0,field(12).toDoubleOrNull()?:0.0,field(13).toDoubleOrNull()?:0.0,field(15),field(16).toLongOrNull()?:0,field(17).toLongOrNull()?:0,field(18).toDoubleOrNull()?:0.0,field(19),field(20),field(22))
}
    private fun parseDecision(text:String):DecisionRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("decision_id,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<16)return null;return DecisionRecord(c[0],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11],c[12],c[15])}
    private fun parsePlan(text:String):PlanRecord?{val l=text.lineSequence().filter{it.isNotBlank()&&!it.startsWith("state,")}.lastOrNull()?:return null;val c=parseCsv(l);if(c.size<12)return null;return PlanRecord(c[0],c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10])}
    private fun parseCsv(line:String):List<String>{val out=mutableListOf<String>();val cur=StringBuilder();var q=false;var i=0;while(i<line.length){val ch=line[i];if(ch=='"'){if(q&&i+1<line.length&&line[i+1]=='"'){cur.append('"');i++}else q=!q}else if(ch==','&&!q){out.add(cur.toString());cur.setLength(0)}else cur.append(ch);i++};out.add(cur.toString());return out}
}
