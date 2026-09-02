#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12180',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r18"',bs,count=1); b.write_text(bs)
rs=r.read_text(); anchor='    suspend fun snapshot()'; assert anchor in rs
fast='''    data class FastTelemetry(val updatedMs: Long=0, val littleKhz: Long=0, val bigKhz: Long=0, val gpuHz: Long=0)\n    private var fastProcess: Process? = null\n    private var fastReader: java.io.BufferedReader? = null\n    private fun ensureFastStream(): java.io.BufferedReader? {\n        if (fastProcess?.isAlive == true && fastReader != null) return fastReader\n        try { fastProcess?.destroy() } catch (_: Throwable) {}\n        return try {\n            val cmd = "while true; do cat /data/adb/djaeger_ai/fast_telemetry 2>/dev/null; echo __DJAEGER_FAST_END__; sleep 0.2; done"\n            val p = ProcessBuilder("su", "-c", cmd).redirectErrorStream(true).start()\n            fastProcess=p; p.inputStream.bufferedReader().also { fastReader=it }\n        } catch (_:Throwable) { fastProcess=null; fastReader=null; null }\n    }\n    suspend fun fastTelemetry(): FastTelemetry = withContext(Dispatchers.IO) {\n        val br=ensureFastStream() ?: return@withContext FastTelemetry(); val map=linkedMapOf<String,String>()\n        try { while(true){ val line=br.readLine() ?: break; if(line=="__DJAEGER_FAST_END__") break; val p=line.trim().split('=',limit=2); if(p.size==2) map[p[0].trim()]=p[1].trim().trim('\\'') } }\n        catch (_:Throwable){ try{fastProcess?.destroy()}catch(_:Throwable){}; fastProcess=null; fastReader=null; return@withContext FastTelemetry() }\n        fun n(k:String)=map[k]?.toLongOrNull()?:0L\n        FastTelemetry(n("UPDATED_MS"),n("CPU_L_CUR"),n("CPU_B_CUR"),n("GPU_CUR"))\n    }\n\n'''
if 'suspend fun fastTelemetry()' not in rs: rs=rs.replace(anchor,fast+anchor,1)
r.write_text(rs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r17 • 4-KEY POOL • REALTIME 1s','CONTROL CENTER • v0.12.1-r18 • FAST TELEMETRY • 200ms')
# Guaranteed composable-body anchor created by r13; insert state immediately before its OutlinedTextField.
needle='OutlinedTextField(value=keyInput'; assert needle in ms
if 'fastTelemetryState' not in ms:
    prefix='''var fastTelemetryState by remember { mutableStateOf(DjaegerRepository.FastTelemetry()) }\n        LaunchedEffect(Unit) { while (true) { fastTelemetryState = repo.fastTelemetry(); kotlinx.coroutines.delay(1) } }\n        Text("FAST TELEMETRY • LITTLE ${fastTelemetryState.littleKhz/1000} MHz • BIG ${fastTelemetryState.bigKhz/1000} MHz • GPU ${fastTelemetryState.gpuHz/1000000} MHz")\n        '''
    ms=ms.replace(needle,prefix+needle,1)
m.write_text(ms)
print('R18_FAST_STREAM=PERSISTENT_ROOT_PROCESS');print('R18_KEYS=R82_EXACT');print('R18_STATE=COMPOSABLE_BOUND');print('R18_FULL_UI=PRESERVED')
