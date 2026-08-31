from pathlib import Path
import re

pkg=Path('app/src/main/java/com/djaeger/controlcenter')
r=pkg/'DjaegerRepository.kt'
m=pkg/'MainActivity.kt'
g=Path('app/build.gradle.kts')

# Version: retain v0.12.1 UI baseline, mark telemetry/runtime fix revision.
gs=g.read_text()
gs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 42',gs,count=1)
gs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r1-djaeger-ai-12.9.50-r2-sync"',gs,count=1)
g.write_text(gs)

s=r.read_text()
# Missing sensor/frequency values use -1 internally; the UI renders them as --.
s=s.replace('data class Telemetry(val epoch:Long=0,val cpuT:Int=0,val gpuT:Int=0,val skinT:Int=0,val batT:Int=0,val littleKhz:Long=0,val bigKhz:Long=0,val gpuHz:Long=0',
'''data class Telemetry(val epoch:Long=0,val cpuT:Int=-1,val gpuT:Int=-1,val skinT:Int=-1,val batT:Int=-1,val littleKhz:Long=-1,val bigKhz:Long=-1,val gpuHz:Long=-1''')

start=s.find('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=s.find('    suspend fun setUserMode',start)
if start<0 or end<0:
    raise SystemExit('Build42 snapshot anchors missing')

new_snapshot=r'''    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){
        val result=su("""
        echo __INSTALLED__; [ -d '$module' ] && echo 1 || echo 0
        echo __VERSION__; sed -n 's/^version=//p' '$module/module.prop' 2>/dev/null | head -n 1
        echo __RUNTIME__; cat '$persistent/runtime_status' 2>/dev/null
        echo __TEL__; tail -n 1 '$module/telemetry.csv' 2>/dev/null
        echo __LIVE__
        printf 'LITTLE_KHZ='; cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq 2>/dev/null || true
        printf 'BIG_KHZ='; cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq 2>/dev/null || true
        printf 'GPU_HZ='; cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null || true
        printf 'BAT_TEMP_RAW='; cat /sys/class/power_supply/battery/temp 2>/dev/null || true
        printf 'BAT_STATUS='; cat /sys/class/power_supply/battery/status 2>/dev/null || true
        printf 'BAT_VOLTAGE_UV='; cat /sys/class/power_supply/battery/voltage_now 2>/dev/null || true
        printf 'BAT_CURRENT_A='; cat /sys/class/power_supply/battery/current_now 2>/dev/null || true
        printf 'BAT_CURRENT_B='; cat /sys/class/power_supply/sm5602_bat/current_now 2>/dev/null || true
        for z in /sys/class/thermal/thermal_zone*; do
          [ -r "$z/type" ] && [ -r "$z/temp" ] || continue
          n=$(cat "$z/type" 2>/dev/null); t=$(cat "$z/temp" 2>/dev/null)
          printf 'THERMAL=%s|%s\n' "$n" "$t"
        done
        echo __BRAIN__; cat '$persistent/local_brain_state' 2>/dev/null
        echo __ENV__; cat '$persistent/adaptive_operating_envelope' 2>/dev/null
        echo __HTTP__; cat '$persistent/gemini_http_state' 2>/dev/null
        echo __SERVER__; cat '$persistent/gemini_server_state' 2>/dev/null
        echo __DECISIONS__; tail -n 16 '$persistent/decision_ledger.csv' 2>/dev/null
        echo __PLANS__; tail -n 16 '$persistent/plan_history.csv' 2>/dev/null
        echo __FRAME__; tail -n 30 '$module/frame_intel.csv' 2>/dev/null
        echo __LOG__; tail -n 120 '$module/controller.log' 2>/dev/null
        """.trimIndent())
        val(rc,out)=result
        if(rc!=0)return@withContext RuntimeState(error=out.ifBlank{"Root permission unavailable"})
        fun section(a:String,b:String?):String{val x=out.substringAfter("__${a}__\n","");return if(b==null)x else x.substringBefore("__${b}__\n","")}
        val installed=section("INSTALLED","VERSION").trim()=="1"
        val moduleVersion=section("VERSION","RUNTIME").trim().ifBlank{"unknown"}
        val rt=section("RUNTIME","TEL").lineSequence().mapNotNull{l->l.split("=",limit=2).takeIf{it.size==2}?.let{it[0] to it[1].trim().trim('\'')}}.toMap()
        val decisions=section("DECISIONS","PLANS").trim()
        val plans=section("PLANS","FRAME").trim()
        val csv=parseTelemetry(section("TEL","LIVE").trim())
        val liveText=section("LIVE","BRAIN")
        val live=mutableMapOf<String,String>()
        val thermals=mutableListOf<Pair<String,Double>>()
        liveText.lineSequence().forEach{line->
            if(line.startsWith("THERMAL=")){
                val q=line.removePrefix("THERMAL=").split('|',limit=2)
                if(q.size==2) q[1].trim().toDoubleOrNull()?.let{v->thermals.add(q[0].trim() to normalizeThermal(v))}
            } else {
                val p=line.indexOf('='); if(p>0) live[line.substring(0,p).trim()]=line.substring(p+1).trim()
            }
        }
        fun maxThermal(match:(String)->Boolean):Int{
            val v=thermals.filter{match(it.first)}.maxOfOrNull{it.second} ?: return -1
            return v.toInt()
        }
        val cpuLive=maxThermal{it.startsWith("cpu-")||it.startsWith("cpuss-")}
        val gpuLive=maxThermal{it.startsWith("gpuss-")}
        val skinLive=maxThermal{it=="sdm-skin-therm-usr"||it.contains("skin",true)}
        val batRaw=live["BAT_TEMP_RAW"]?.toDoubleOrNull()
        val batLive=batRaw?.let{if(kotlin.math.abs(it)>1000.0) it/1000.0 else if(kotlin.math.abs(it)>100.0) it/10.0 else it}?.toInt() ?: -1
        fun positiveLong(k:String)=live[k]?.toLongOrNull()?.takeIf{it>0}
        val little=positiveLong("LITTLE_KHZ") ?: csv.littleKhz.takeIf{it>0} ?: -1
        val big=positiveLong("BIG_KHZ") ?: csv.bigKhz.takeIf{it>0} ?: -1
        val gpu=positiveLong("GPU_HZ") ?: csv.gpuHz.takeIf{it>0} ?: -1
        val currentA=live["BAT_CURRENT_A"]?.toLongOrNull()
        val currentB=live["BAT_CURRENT_B"]?.toLongOrNull()
        val current=when{
            currentB!=null && kotlin.math.abs(currentB)>=10000L -> currentB
            currentA!=null && kotlin.math.abs(currentA)>=10000L -> currentA
            else -> csv.currentUa.takeIf{it!=0L} ?: 0L
        }
        val voltage=positiveLong("BAT_VOLTAGE_UV") ?: csv.voltageUv.takeIf{it>0} ?: 0L
        val power=if(current!=0L&&voltage>0L) kotlin.math.abs(current.toDouble()*voltage.toDouble())/1_000_000_000.0 else csv.powerMw
        val now=System.currentTimeMillis()/1000
        val tel=csv.copy(
            epoch=if(csv.epoch>0) csv.epoch else now,
            cpuT=if(cpuLive>=0)cpuLive else csv.cpuT,
            gpuT=if(gpuLive>=0)gpuLive else csv.gpuT,
            skinT=if(skinLive>=0)skinLive else csv.skinT,
            batT=if(batLive>=0)batLive else csv.batT,
            littleKhz=little,bigKhz=big,gpuHz=gpu,
            batteryStatus=live["BAT_STATUS"]?.ifBlank{null}?:csv.batteryStatus,
            currentUa=current,voltageUv=voltage,powerMw=power,
            powerValid=if(current!=0L&&voltage>0L)"VALID" else csv.powerValid,
            powerReason=if(current!=0L&&voltage>0L)"LIVE_POWER_SUPPLY" else csv.powerReason
        )
        val age=now-tel.epoch
        RuntimeState(root=true,sampleFresh=(tel.cpuT>=0||tel.gpuT>=0||tel.littleKhz>0||tel.gpuHz>0)&&age in 0..5,installed=installed,active=rt["active"]?:"0",game=rt["game"]?:"NA",window=rt["window_mode"]?:"INACTIVE",controllerPid=rt["controller_pid"]?:"",predictorPid=rt["predictor_pid"]?:"",updated=rt["updated_at"]?.toLongOrNull()?:0,userMode=rt["user_mode"]?:"AUTO",moduleVersion=moduleVersion,telemetry=tel,brain=section("BRAIN","ENV").trim(),envelope=section("ENV","HTTP").trim(),geminiHttp=section("HTTP","SERVER").trim(),geminiServer=section("SERVER","DECISIONS").trim(),decisions=decisions,plans=plans,frameIntel=section("FRAME","LOG").trim(),log=section("LOG",null).trim(),latestDecision=parseDecision(decisions),latestPlan=parsePlan(plans))
    }

    private fun normalizeThermal(v:Double):Double = if(kotlin.math.abs(v)>1000.0) v/1000.0 else v
'''
s=s[:start]+new_snapshot+s[end:]
r.write_text(s)

s=m.read_text()
s=s.replace('CONTROL CENTER • v0.12.1 • DJAEGER-AI v12.9.50-r1 SYNC • REALTIME 1s','CONTROL CENTER • v0.12.1-r1 • DJAEGER-AI v12.9.50-r2 SYNC • REALTIME 1s')
s=s.replace('Target module: v12.9.50-r1','Target module: v12.9.50-r2')
# Overview formatting: zero is not used as a fake missing sensor/frequency anymore.
old='''@Composable fun Overview(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS","%.1f".format(s.telemetry.fps),Modifier.weight(1f));Metric("Frame","%.1f ms".format(s.telemetry.frameMs),Modifier.weight(1f));Metric("Jank","%.1f%%".format(s.telemetry.jank),Modifier.weight(1f))};ThermalRow(s);BoxCard("PERFORMANCE","Little: ${s.telemetry.littleKhz/1000} MHz\nBig: ${s.telemetry.bigKhz/1000} MHz\nGPU: ${s.telemetry.gpuHz/1_000_000} MHz\nProfile: ${s.telemetry.profile}\nP95/P99: ${s.telemetry.p95} / ${s.telemetry.p99} ms");BoxCard("POWER","${s.telemetry.batteryStatus} • %.1f mW".format(s.telemetry.powerMw)+"\n${s.telemetry.currentUa} µA • ${s.telemetry.voltageUv} µV\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}}'''
new='''@Composable fun Overview(s:RuntimeState){
    fun mhz(v:Long,div:Long)=if(v>0)"${v/div} MHz" else "--"
    fun frame(v:Double,suffix:String)=if(s.active=="1"&&v>0)"%.1f%s".format(v,suffix) else "--"
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS",frame(s.telemetry.fps,""),Modifier.weight(1f));Metric("Frame",frame(s.telemetry.frameMs," ms"),Modifier.weight(1f));Metric("Jank",frame(s.telemetry.jank,"%"),Modifier.weight(1f))};ThermalRow(s);BoxCard("PERFORMANCE","Little: ${mhz(s.telemetry.littleKhz,1000)}\nBig: ${mhz(s.telemetry.bigKhz,1000)}\nGPU: ${mhz(s.telemetry.gpuHz,1_000_000)}\nProfile: ${s.telemetry.profile.ifBlank{"--"}}\nP95/P99: ${if(s.active=="1"&&s.telemetry.p95>0)"${s.telemetry.p95} / ${s.telemetry.p99} ms" else "--"}");BoxCard("POWER","${s.telemetry.batteryStatus} • ${if(s.telemetry.powerMw>0)"%.1f mW".format(s.telemetry.powerMw) else "--"}\n${if(s.telemetry.currentUa!=0L)"${s.telemetry.currentUa} µA" else "--"} • ${if(s.telemetry.voltageUv>0)"${s.telemetry.voltageUv} µV" else "--"}\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}
}'''
if old not in s: raise SystemExit('Build42 Overview anchor missing')
s=s.replace(old,new,1)
old='''@Composable fun ThermalRow(s:RuntimeState){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Thermal("CPU",s.telemetry.cpuT,Modifier.weight(1f));Thermal("GPU",s.telemetry.gpuT,Modifier.weight(1f));Thermal("Skin",s.telemetry.skinT,Modifier.weight(1f));Thermal("Battery",s.telemetry.batT,Modifier.weight(1f))}}'''
new='''@Composable fun ThermalRow(s:RuntimeState){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Thermal("CPU",s.telemetry.cpuT,Modifier.weight(1f));Thermal("GPU",s.telemetry.gpuT,Modifier.weight(1f));Thermal("Skin",s.telemetry.skinT,Modifier.weight(1f));Thermal("Battery",s.telemetry.batT,Modifier.weight(1f))}}'''
# Thermal composable itself needs missing rendering.
# Locate compact one-line definition generated by baseline.
thermal_pat=r'@Composable fun Thermal\(name:String,t:Int,mod:Modifier=Modifier\)\{.*?\n'
mt=re.search(thermal_pat,s)
if not mt: raise SystemExit('Build42 Thermal function missing')
thermal_new='''@Composable fun Thermal(name:String,t:Int,mod:Modifier=Modifier){val c=when{t<0->Muted;t>=55->Color(0xFFFF5D73);t>=45->Amber;else->Green};Card(mod,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(name,color=Muted,style=MaterialTheme.typography.labelMedium);Text(if(t>=0)"${t}°C" else "--",color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}\n'''
s=s[:mt.start()]+thermal_new+s[mt.end():]
m.write_text(s)

# Static regression checks.
rs=r.read_text(); ms=m.read_text()
for q in ('LITTLE_KHZ=','GPU_HZ=','BAT_TEMP_RAW=','THERMAL=','sm5602_bat/current_now','LIVE_POWER_SUPPLY'):
    if q not in rs: raise SystemExit('Build42 missing telemetry path: '+q)
if '0°C' in ms: raise SystemExit('Build42 fake-zero thermal rendering remains')
if any(x in (rs+ms) for x in ('echo 0 > /sys','tee /sys','settings put','setprop','force-stop')):
    raise SystemExit('Build42 mutation path detected')
print('Build42 applied: multi-source read-only telemetry + missing-value rendering + r2 sync')