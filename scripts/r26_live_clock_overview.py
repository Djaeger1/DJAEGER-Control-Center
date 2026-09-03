#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12260',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r26"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('v0.12.1-r25','v0.12.1-r26').replace('LIVE GEMINI + VAULT TRUTH','LIVE CLOCKS + GEMINI TRUTH')

# 0°C from missing/idle sensors is not a real reading. Render unavailable as dash.
ms=ms.replace('private fun tempText(value:Int)=if(value>=0)"$value°C" else "—"','private fun tempText(value:Int)=if(value>0)"$value°C" else "—"')
ms=ms.replace('val c=when{t<0->Muted;t>=50->Red;t>=43->Amber;else->Green}','val c=when{t<=0->Muted;t>=50->Red;t>=43->Amber;else->Green}')
ms=ms.replace('Thermal("CPU",s.telemetry.cpuT','Thermal("CPU TEMP",s.telemetry.cpuT').replace('Thermal("GPU",s.telemetry.gpuT','Thermal("GPU TEMP",s.telemetry.gpuT').replace('Thermal("Skin",s.telemetry.skinT','Thermal("SKIN",s.telemetry.skinT').replace('Thermal("Battery",s.telemetry.batT','Thermal("BATTERY",s.telemetry.batT')

# Add an explicit live clock row to Overview using the proven R18 persistent
# root fast-telemetry stream. It remains local/read-only and does not touch sysfs.
insert_before='@Composable fun StatusCard(s:RuntimeState)'
assert insert_before in ms,'StatusCard anchor missing'
clock_fn='''@Composable fun LiveClockRow(){
    val repo=remember{DjaegerRepository()}
    var f by remember{mutableStateOf(DjaegerRepository.FastTelemetry())}
    LaunchedEffect(Unit){while(true){f=repo.fastTelemetry();delay(200)}}
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
        Metric("LITTLE CPU",if(f.littleKhz>0)"${f.littleKhz/1000} MHz" else "—",Modifier.weight(1f))
        Metric("BIG CPU",if(f.bigKhz>0)"${f.bigKhz/1000} MHz" else "—",Modifier.weight(1f))
        Metric("GPU",if(f.gpuHz>0)"${f.gpuHz/1000000} MHz" else "—",Modifier.weight(1f))
    }
}

'''
if '@Composable fun LiveClockRow()' not in ms:
    ms=ms.replace(insert_before,clock_fn+insert_before,1)

# R24/R25 changed the exact Overview formatting. Find the Overview function and
# inject before its first ThermalRow call instead of relying on a brittle string.
ov=ms.find('@Composable fun Overview(s:RuntimeState)')
assert ov>=0,'Overview missing'
tr=ms.find('ThermalRow(s);',ov)
assert tr>ov,'Overview ThermalRow missing'
if 'LiveClockRow();' not in ms[ov:tr]:
    ms=ms[:tr]+'LiveClockRow();'+ms[tr:]

# R18 fast telemetry text in AI used default on-background color; force readable color.
old='Text("FAST TELEMETRY • LITTLE ${fastTelemetryState.littleKhz/1000} MHz • BIG ${fastTelemetryState.bigKhz/1000} MHz • GPU ${fastTelemetryState.gpuHz/1000000} MHz")'
new='Text("FAST TELEMETRY • LITTLE ${fastTelemetryState.littleKhz/1000} MHz • BIG ${fastTelemetryState.bigKhz/1000} MHz • GPU ${fastTelemetryState.gpuHz/1000000} MHz",color=Green)'
ms=ms.replace(old,new)

m.write_text(ms)
M=m.read_text()
checks={
 'R26_VERSION':'v0.12.1-r26' in M,
 'LIVE_CLOCK_ROW':'@Composable fun LiveClockRow()' in M and 'LiveClockRow();ThermalRow(s)' in M,
 'FAST_STREAM_REUSED':'repo.fastTelemetry()' in M,
 'CLOCKS_MHZ':'LITTLE CPU' in M and 'BIG CPU' in M and 'GPU' in M and 'MHz' in M,
 'ZERO_TEMP_NOT_REAL':'private fun tempText(value:Int)=if(value>0)' in M,
 'AI_FAST_TEXT_VISIBLE':'FAST TELEMETRY' in M and 'color=Green' in M,
}
for k,v in checks.items(): print(f'{k}={"PASS" if v else "FAIL"}')
bad=[k for k,v in checks.items() if not v]; assert not bad,','.join(bad)
