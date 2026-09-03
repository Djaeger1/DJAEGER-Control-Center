#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12270',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r27"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
# R18 only parsed clocks even though backend fast_telemetry already carries CPU_T/GPU_T/SKIN_T/BAT_T.
old='data class FastTelemetry(val updatedMs: Long=0, val littleKhz: Long=0, val bigKhz: Long=0, val gpuHz: Long=0)'
new='data class FastTelemetry(val updatedMs: Long=0, val littleKhz: Long=0, val bigKhz: Long=0, val gpuHz: Long=0, val cpuT: Long=0, val gpuT: Long=0, val skinT: Long=0, val batT: Long=0)'
assert old in rs,'FastTelemetry data class anchor missing'
rs=rs.replace(old,new,1)
oldret='FastTelemetry(n("UPDATED_MS"),n("CPU_L_CUR"),n("CPU_B_CUR"),n("GPU_CUR"))'
newret='FastTelemetry(n("UPDATED_MS"),n("CPU_L_CUR"),n("CPU_B_CUR"),n("GPU_CUR"),n("CPU_T"),n("GPU_T"),n("SKIN_T"),n("BAT_T"))'
assert oldret in rs,'FastTelemetry parser anchor missing'
rs=rs.replace(oldret,newret,1)

# Replace the stale file repeater with one persistent read-only root observer that samples
# clocks + thermal zones directly while Control Center is open. This keeps idle readings live
# without changing DJAEGER kernel authority, network state, routing, DNS, or actuator paths.
oldcmd='val cmd = "while true; do cat /data/adb/djaeger_ai/fast_telemetry 2>/dev/null; echo __DJAEGER_FAST_END__; sleep 0.2; done"'
assert oldcmd in rs,'R18 fast stream command anchor missing'
cmd='val cmd = "while true; do L=\\$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq 2>/dev/null); B=\\$(cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq 2>/dev/null); G=\\$(cat /sys/class/kgsl/kgsl-3d0/devfreq/cur_freq 2>/dev/null); CPU=0; GPUT=0; SKIN=0; BAT=0; for z in /sys/class/thermal/thermal_zone*; do N=\\$(cat \\$z/type 2>/dev/null); T=\\$(cat \\$z/temp 2>/dev/null); case \\$T in \'\'|*[!0-9-]*) T=0;; *) [ \\$T -gt 1000 ] 2>/dev/null && T=\\$((T/1000));; esac; case \\$N in cpu-*-usr|cpuss-*-usr) [ \\$T -gt \\$CPU ] 2>/dev/null && CPU=\\$T;; gpuss-*-usr) [ \\$T -gt \\$GPUT ] 2>/dev/null && GPUT=\\$T;; sdm-skin-therm-usr) SKIN=\\$T;; battery|sm5602_bat) [ \\$T -gt \\$BAT ] 2>/dev/null && BAT=\\$T;; esac; done; NOW=\\$(date +%s%3N 2>/dev/null); echo UPDATED_MS=\\$NOW; echo CPU_L_CUR=\\$L; echo CPU_B_CUR=\\$B; echo GPU_CUR=\\$G; echo CPU_T=\\$CPU; echo GPU_T=\\$GPUT; echo SKIN_T=\\$SKIN; echo BAT_T=\\$BAT; echo __DJAEGER_FAST_END__; sleep 1; done"'
rs=rs.replace(oldcmd,cmd,1)
r.write_text(rs)

ms=m.read_text()
ms=ms.replace('v0.12.1-r26','v0.12.1-r27').replace('LIVE CLOCKS + GEMINI TRUTH','LIVE HARDWARE + GEMINI TRUTH')
# Extend the proven R26 live row with temperatures from the SAME persistent stream.
anchor='''        Metric("GPU",if(f.gpuHz>0)"${f.gpuHz/1000000} MHz" else "—",Modifier.weight(1f))\n    }\n}\n'''
assert anchor in ms,'R26 LiveClockRow end anchor missing'
replacement='''        Metric("GPU",if(f.gpuHz>0)"${f.gpuHz/1000000} MHz" else "—",Modifier.weight(1f))\n    }\n    Spacer(Modifier.height(8.dp))\n    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n        Thermal("CPU TEMP",f.cpuT.toInt(),Modifier.weight(1f))\n        Thermal("GPU TEMP",f.gpuT.toInt(),Modifier.weight(1f))\n        Thermal("SKIN",f.skinT.toInt(),Modifier.weight(1f))\n        Thermal("BATTERY",f.batT.toInt(),Modifier.weight(1f))\n    }\n}\n'''
ms=ms.replace(anchor,replacement,1)
# Remove the old session-bound thermal row from Overview; otherwise it would still show dashes.
ov=ms.find('@Composable fun Overview(s:RuntimeState)')
assert ov>=0,'Overview missing'
tr=ms.find('ThermalRow(s);',ov)
assert tr>ov,'legacy Overview ThermalRow missing'
ms=ms[:tr]+ms[tr+len('ThermalRow(s);'):]
m.write_text(ms)

R=r.read_text(); M=m.read_text()
checks={
 'R27_VERSION':'v0.12.1-r27' in M,
 'FAST_TEMPS_PARSED':all(x in R for x in ['val cpuT: Long=0','val gpuT: Long=0','val skinT: Long=0','val batT: Long=0','n("CPU_T")','n("GPU_T")','n("SKIN_T")','n("BAT_T")']),
 'LIVE_SYSFS_READ_ONLY':'/sys/class/thermal/thermal_zone*' in R and '/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq' in R,
 'LIVE_TEMP_VISIBLE':all(x in M for x in ['Thermal("CPU TEMP",f.cpuT.toInt()','Thermal("GPU TEMP",f.gpuT.toInt()','Thermal("SKIN",f.skinT.toInt()','Thermal("BATTERY",f.batT.toInt()']),
 'NO_LEGACY_OVERVIEW_THERMAL':'ThermalRow(s);' not in M[ov:ms.find('@Composable fun StatusCard',ov)],
 'NO_NETWORK_MUTATION':not any(x in R for x in ['iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns']),
 'NO_SYSFS_WRITES':not any(x in R for x in ['> /sys/','tee /sys/','chmod /sys/','chown /sys/']),
}
for k,v in checks.items(): print(f'{k}={"PASS" if v else "FAIL"}')
bad=[k for k,v in checks.items() if not v]; assert not bad,','.join(bad)
print('R27_ROOT_CAUSE=R18_FAST_TELEMETRY_PARSER_DROPPED_THERMAL_FIELDS')
print('R27_LIVE_TEMPERATURES=SAME_PERSISTENT_READ_ONLY_STREAM')
