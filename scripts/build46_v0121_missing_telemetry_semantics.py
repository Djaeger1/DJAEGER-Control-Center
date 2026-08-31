from pathlib import Path
import re
r=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt')
m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
rs=r.read_text(); ms=m.read_text()
# Empty CSV is unknown, not real 0C/0MHz.
rs=rs.replace('field(0).toLongOrNull()?:0,field(1).toIntOrNull()?:0,field(2).toIntOrNull()?:0,field(3).toIntOrNull()?:0,field(4).toIntOrNull()?:0,field(5).toLongOrNull()?:0,field(6).toLongOrNull()?:0,field(7).toLongOrNull()?:0',
'field(0).toLongOrNull()?:0,field(1).toIntOrNull()?:-1,field(2).toIntOrNull()?:-1,field(3).toIntOrNull()?:-1,field(4).toIntOrNull()?:-1,field(5).toLongOrNull()?:-1,field(6).toLongOrNull()?:-1,field(7).toLongOrNull()?:-1')
r.write_text(rs)
old='@Composable fun Thermal(label:String,t:Int,m:Modifier){val c=when{t>=50->Red;t>=43->Amber;else->Green};Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text("$t°C",color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}'
new='@Composable fun Thermal(label:String,t:Int,m:Modifier){val c=when{t<0->Muted;t>=50->Red;t>=43->Amber;else->Green};Card(m,colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(12.dp)){Text(label,color=Muted,style=MaterialTheme.typography.labelMedium);Text(if(t>=0)"$t°C" else "—",color=c,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.titleMedium)}}}'
if old not in ms: raise SystemExit('Build46 thermal anchor missing')
ms=ms.replace(old,new,1)
# Preserve compact layout, only make missing clock values explicit.
ms=ms.replace('${s.telemetry.littleKhz/1000} MHz','${if(s.telemetry.littleKhz>0) "${s.telemetry.littleKhz/1000} MHz" else "—"}',1)
ms=ms.replace('${s.telemetry.bigKhz/1000} MHz','${if(s.telemetry.bigKhz>0) "${s.telemetry.bigKhz/1000} MHz" else "—"}',1)
ms=ms.replace('${s.telemetry.gpuHz/1_000_000} MHz','${if(s.telemetry.gpuHz>0) "${s.telemetry.gpuHz/1_000_000} MHz" else "—"}',1)
m.write_text(ms)
if 'Text("$t°C"' in ms: raise SystemExit('Build46 old fake-zero thermal renderer remains')
print('Build46 applied: unavailable temperature/frequency telemetry is explicit, not fake zero')