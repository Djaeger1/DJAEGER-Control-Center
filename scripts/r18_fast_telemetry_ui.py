#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2'); b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12180',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r18"',bs,count=1); b.write_text(bs)
rs=r.read_text()
anchor='    suspend fun snapshot()'
assert anchor in rs
fast='''    data class FastTelemetry(val epoch: Long=0, val littleKhz: Long=0, val bigKhz: Long=0, val gpuMhz: Long=0, val raw: String="")\n\n    suspend fun fastTelemetry(): FastTelemetry = withContext(Dispatchers.IO) {\n        val (rc, out) = su("cat /data/adb/djaeger_ai/fast_telemetry 2>/dev/null", 1500)\n        if (rc != 0 || out.isBlank()) return@withContext FastTelemetry()\n        val map = out.lineSequence().mapNotNull { line ->\n            val p=line.trim().split('=', limit=2); if(p.size==2) p[0].trim() to p[1].trim() else null\n        }.toMap()\n        fun n(vararg k:String):Long { for(x in k){ map[x]?.toLongOrNull()?.let{return it} }; return 0L }\n        FastTelemetry(n("epoch","updated_at","ts"), n("cpu_little_khz","little_khz","little"), n("cpu_big_khz","big_khz","big"), n("gpu_mhz","gpu"), out)\n    }\n\n'''
if 'suspend fun fastTelemetry()' not in rs: rs=rs.replace(anchor,fast+anchor,1)
r.write_text(rs)
ms=m.read_text(); ms=ms.replace('CONTROL CENTER • v0.12.1-r17 • 4-KEY POOL • REALTIME 1s','CONTROL CENTER • v0.12.1-r18 • FAST TELEMETRY • 200ms')
# Keep the existing full UI intact; add a separate fast state loop and compact live line.
needle='val scope = rememberCoroutineScope()'
if needle in ms and 'fastTelemetryState' not in ms:
    ms=ms.replace(needle, needle+'\n    var fastTelemetryState by remember { mutableStateOf(DjaegerRepository.FastTelemetry()) }\n    LaunchedEffect(Unit) { while (true) { fastTelemetryState = repo.fastTelemetry(); kotlinx.coroutines.delay(200) } }',1)
# Insert live line immediately after header occurrence when possible.
header='CONTROL CENTER • v0.12.1-r18 • FAST TELEMETRY • 200ms'
pos=ms.find(header)
if pos>=0 and 'FAST • LITTLE' not in ms:
    line_end=ms.find('\n',pos)
    live='\n                Text("FAST • LITTLE ${fastTelemetryState.littleKhz/1000} MHz • BIG ${fastTelemetryState.bigKhz/1000} MHz • GPU ${fastTelemetryState.gpuMhz} MHz", style=MaterialTheme.typography.bodySmall)'
    ms=ms[:line_end]+live+ms[line_end:]
m.write_text(ms)
print('R18_FAST_TELEMETRY=200MS_READ_ONLY')
print('R18_FULL_UI=PRESERVED')
print('R18_AI_CADENCE=UNCHANGED')
