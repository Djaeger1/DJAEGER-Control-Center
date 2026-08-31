from pathlib import Path
import re
m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'); s=m.read_text()
s=s.replace('CONTROL CENTER • v0.12.1 • DJAEGER-AI v12.9.50-r1 SYNC • REALTIME 1s','CONTROL CENTER • v0.12.1-r1 • DJAEGER-AI v12.9.50-r2 SYNC • REALTIME 1s')
s=s.replace('Target module: v12.9.50-r1','Target module: v12.9.50-r2')
new_overview='''@Composable fun Overview(s:RuntimeState){fun mhz(v:Long,d:Long)=if(v>0)"${v/d} MHz" else "--";fun fr(v:Double,u:String)=if(s.active=="1"&&v>0)"%.1f%s".format(v,u) else "--";Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){if(s.error.isNotBlank())BoxCard("ROOT / CONNECTION",s.error);StatusCard(s);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric("FPS",fr(s.telemetry.fps,""),Modifier.weight(1f));Metric("Frame",fr(s.telemetry.frameMs," ms"),Modifier.weight(1f));Metric("Jank",fr(s.telemetry.jank,"%"),Modifier.weight(1f))};ThermalRow(s);BoxCard("PERFORMANCE","Little: ${mhz(s.telemetry.littleKhz,1000)}\\nBig: ${mhz(s.telemetry.bigKhz,1000)}\\nGPU: ${mhz(s.telemetry.gpuHz,1_000_000)}\\nProfile: ${s.telemetry.profile.ifBlank{"--"}}\\nP95/P99: ${if(s.active=="1"&&s.telemetry.p95>0)"${s.telemetry.p95} / ${s.telemetry.p99} ms" else "--"}");BoxCard("POWER","${s.telemetry.batteryStatus} • ${if(s.telemetry.powerMw>0)"%.1f mW".format(s.telemetry.powerMw) else "--"}\\n${if(s.telemetry.currentUa!=0L)"${s.telemetry.currentUa} µA" else "--"} • ${if(s.telemetry.voltageUv>0)"${s.telemetry.voltageUv} µV" else "--"}\\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}}
'''
s,n=re.subn(r'@Composable fun Overview\(s:RuntimeState\)\{.*?(?=@Composable fun StatusCard)',new_overview,s,flags=re.S)
if n!=1: raise SystemExit(f'Build44 Overview replacements={n}')
thermal='''@Composable fun Thermal(label:String,t:Int,m:Modifier){val c=when{t<0->Muted;t>=50->Red;t>=43->Amber;else->Green};Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(if(t>=0)"${t}°C" else "--",color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}
'''
s,n=re.subn(r'@Composable fun Thermal\(label:String,t:Int,m:Modifier\)\{.*?\}\}\}\n',thermal,s,count=1,flags=re.S)
if n!=1: raise SystemExit(f'Build44 Thermal replacements={n}')
m.write_text(s)
if 'Text("$t°C"' in s: raise SystemExit('Build44 fake thermal zero renderer remains')
print('Build44 applied: missing telemetry values render as --; v0.12.1 compact UI preserved')