from pathlib import Path
import re

pkg=Path('app/src/main/java/com/djaeger/controlcenter')
r=pkg/'DjaegerRepository.kt'
m=pkg/'MainActivity.kt'
g=Path('app/build.gradle.kts')

gs=g.read_text()
gs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 45',gs,count=1)
gs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r1-live-telemetry-djaeger-r2"',gs,count=1)
g.write_text(gs)

s=r.read_text()
start=s.find('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=s.find('    suspend fun setUserMode',start)
if start<0 or end<0: raise SystemExit('Build45 snapshot anchors missing')

# Compile-safe: no Kotlin interpolation of shell variables is used. Thermal readings use
# direct sysfs scan encoded by a helper shell with ${'$'} escaped explicitly.
new=r'''    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){
        val dollar = '$'
        val liveCmd = """
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
        fun maxTemp(test:(String)->Boolean):Int=thermals.filter{test(it.first)}.maxOfOrNull{it.second}?.toInt()?:0
        val cpuLive=maxTemp{it.startsWith("cpu-")||it.startsWith("cpuss-")}
        val gpuLive=maxTemp{it.startsWith("gpuss-")}
        val skinLive=maxTemp{it.contains("skin",ignoreCase=true)}
        val br=live["BAT_TEMP_RAW"]?.toDoubleOrNull()
        val batLive=if(br==null)0 else (if(kotlin.math.abs(br)>1000.0)br/1000.0 else if(kotlin.math.abs(br)>100.0)br/10.0 else br).toInt()
        fun pos(key:String):Long?=live[key]?.toLongOrNull()?.takeIf{it>0}
        val little=pos("LITTLE_KHZ")?:csv.littleKhz
        val big=pos("BIG_KHZ")?:csv.bigKhz
        val gpu=pos("GPU_HZ")?:csv.gpuHz
        val ca=live["BAT_CURRENT_A"]?.toLongOrNull()
        val cb=live["BAT_CURRENT_B"]?.toLongOrNull()
        val current=when{cb!=null&&kotlin.math.abs(cb)>=10000L->cb;ca!=null&&kotlin.math.abs(ca)>=10000L->ca;else->csv.currentUa}
        val voltage=pos("BAT_VOLTAGE_UV")?:csv.voltageUv
        val power=if(current!=0L&&voltage>0L)kotlin.math.abs(current.toDouble()*voltage.toDouble())/1_000_000_000.0 else csv.powerMw
        val tel=csv.copy(
            cpuT=if(cpuLive>0)cpuLive else csv.cpuT,
            gpuT=if(gpuLive>0)gpuLive else csv.gpuT,
            skinT=if(skinLive>0)skinLive else csv.skinT,
            batT=if(batLive>0)batLive else csv.batT,
            littleKhz=little,bigKhz=big,gpuHz=gpu,
            batteryStatus=live["BAT_STATUS"]?.takeIf{it.isNotBlank()}?:csv.batteryStatus,
            currentUa=current,voltageUv=voltage,powerMw=power,
            powerValid=if(current!=0L&&voltage>0L)"VALID" else csv.powerValid,
            powerReason=if(current!=0L&&voltage>0L)"LIVE_POWER_SUPPLY" else csv.powerReason
        )
        val now=System.currentTimeMillis()/1000;val age=now-tel.epoch
        val decisions=section("DECISIONS","PLANS").trim();val plans=section("PLANS","FRAME").trim()
        RuntimeState(root=true,sampleFresh=(tel.cpuT>0||tel.gpuT>0||tel.littleKhz>0||tel.gpuHz>0)&&(tel.epoch==0L||age in 0..5),installed=installed,active=rt["active"]?:"0",game=rt["game"]?:"NA",window=rt["window_mode"]?:"INACTIVE",controllerPid=rt["controller_pid"]?:"",predictorPid=rt["predictor_pid"]?:"",updated=rt["updated_at"]?.toLongOrNull()?:0,userMode=rt["user_mode"]?:"AUTO",moduleVersion=moduleVersion,telemetry=tel,brain=section("BRAIN","ENV").trim(),envelope=section("ENV","HTTP").trim(),geminiHttp=section("HTTP","SERVER").trim(),geminiServer=section("SERVER","DECISIONS").trim(),decisions=decisions,plans=plans,frameIntel=section("FRAME","LOG").trim(),log=section("LOG",null).trim(),latestDecision=parseDecision(decisions),latestPlan=parsePlan(plans))
    }

'''
s=s[:start]+new+s[end:]
r.write_text(s)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1 • DJAEGER-AI v12.9.50-r1 SYNC • REALTIME 1s','CONTROL CENTER • v0.12.1-r1 • DJAEGER-AI v12.9.50-r2 SYNC • REALTIME 1s')
ms=ms.replace('Target module: v12.9.50-r1','Target module: v12.9.50-r2')
m.write_text(ms)

# Fail closed on mutation paths; this patch is observation-only except retained trusted mode/Gemini CLI.
alltext=r.read_text()+m.read_text()
for forbidden in ('echo 0 > /sys','tee /sys','settings put','setprop','force-stop'):
    if forbidden in alltext: raise SystemExit('Build45 mutation path: '+forbidden)
for req in ('LITTLE_KHZ=','BIG_KHZ=','GPU_HZ=','BAT_TEMP_RAW=','THERMAL=','LIVE_POWER_SUPPLY'):
    if req not in alltext: raise SystemExit('Build45 missing '+req)
print('Build45 applied: compile-safe direct read-only live telemetry bridge')