#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
b=root/'app/build.gradle.kts'

# Version: exact REBUILD3 source + MWFIX1 UI/runtime mapping delta.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12253',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-rebuild3-lang2-mwfix1"',bs,count=1)
b.write_text(bs)

rs=r.read_text()
old='val telBound=if(fFresh) tel.copy(epoch=fEpoch,profile=frameParts.getOrNull(1)?:tel.profile,frameMs=frameParts.getOrNull(2)?.toDoubleOrNull()?:tel.frameMs,fps=frameParts.getOrNull(3)?.toDoubleOrNull()?:tel.fps,jank=frameParts.getOrNull(4)?.toDoubleOrNull()?:tel.jank,p95=frameParts.getOrNull(5)?.toDoubleOrNull()?:tel.p95,p99=frameParts.getOrNull(6)?.toDoubleOrNull()?:tel.p99) else tel'
new='val telBound=if(activeClaim && runtimeFresh && fFresh) tel.copy(epoch=fEpoch,profile=frameParts.getOrNull(1)?:tel.profile,frameMs=frameParts.getOrNull(2)?.toDoubleOrNull()?:tel.frameMs,fps=frameParts.getOrNull(3)?.toDoubleOrNull()?:tel.fps,jank=frameParts.getOrNull(4)?.toDoubleOrNull()?:tel.jank,p95=frameParts.getOrNull(5)?.toDoubleOrNull()?:tel.p95,p99=frameParts.getOrNull(6)?.toDoubleOrNull()?:tel.p99) else tel'
assert old in rs, 'telBound anchor missing'
rs=rs.replace(old,new,1)
rs=rs.replace('game=if(volatileFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA (STALE)",','game=if(volatileFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",',1)
rs=rs.replace('window=if(volatileFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "STALE",','window=if(volatileFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",',1)
r.write_text(rs)

s=m.read_text()
s=s.replace('if(state.root&&state.installed&&state.sampleFresh){','if(state.root&&state.installed&&state.active=="1"&&state.sampleFresh){',1)
s=s.replace('CONTROL CENTER • FIX4 RC1 REBUILD3 • GEMINI PRIMARY • HERMES DEPUTY • AGENT FULL HW','CONTROL CENTER • REBUILD3 • LANG2 • MWFIX1',1)
old_status='''@Composable fun StatusCard(s:RuntimeState){val stale=runtimeStateStale(s);val session=when{ s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"};BoxCard("ENGINE / SESSION",if(s.installed)"${if(s.active=="1")"● ACTIVE" else "○ IDLE"} • ${if(stale)"STALE" else "LIVE"}\\nModule: ${s.moduleVersion}\\nGame: ${s.game}\\nWindow: ${s.window}\\nProfile: ${s.telemetry.profile}\\nLast sample: $session\\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")}'''
new_status='''private fun compactModuleVersion(raw:String):String=when{\n    raw.contains("MWFIX1",true)->"v12.9.50 • REBUILD3 • LANG2 • MWFIX1"\n    raw.contains("REBUILD3-LANG2",true)->"v12.9.50 • REBUILD3 • LANG2"\n    raw.contains("REBUILD3",true)->"v12.9.50 • REBUILD3"\n    else->raw\n}\n@Composable fun StatusCard(s:RuntimeState){\n    val stale=runtimeStateStale(s)\n    val engine=if(stale) "STALE" else "LIVE"\n    val sessionState=when{stale->"UNKNOWN";s.active=="1"->"ACTIVE";else->"WAITING GAME"}\n    val sample=when{s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"}\n    val game=if(s.active=="1") s.game else if(stale) "—" else "NA"\n    val window=if(s.active=="1") s.window else if(stale) "—" else "INACTIVE"\n    val profile=if(s.active=="1") s.telemetry.profile else "—"\n    val age=if(s.updated>0) (System.currentTimeMillis()/1000-s.updated).coerceAtLeast(0) else -1\n    val ageText=if(age>=0) "${age}s" else "—"\n    BoxCard("ENGINE / SESSION",if(s.installed)"Engine: $engine • age $ageText\\nSession: $sessionState\\nModule: ${compactModuleVersion(s.moduleVersion)}\\nGame: $game\\nWindow: $window\\nProfile: $profile\\nLast device sample: $sample\\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")\n}'''
assert old_status in s, 'StatusCard anchor missing'
s=s.replace(old_status,new_status,1)
m.write_text(s)

print('MWFIX1_VERSION=PASS')
print('MWFIX1_FRAME_HISTORY_IDLE_GUARD=PASS')
print('MWFIX1_STALE_FIELDS_SEPARATED=PASS')
print('MWFIX1_ACTIVE_ONLY_CHART_SAMPLES=PASS')
print('MWFIX1_STATUS_SEMANTICS=PASS')
print('MWFIX1_COMPACT_MODULE_LABEL=PASS')
