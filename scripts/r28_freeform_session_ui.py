#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12280',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r28"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r27 • LIVE HARDWARE + GEMINI TRUTH','CONTROL CENTER • v0.12.1-r28 • LIVE HARDWARE',1)

# R28 freeform navigation: the old ScrollableTabRow centers the selected tab,
# which visibly clips the first/last labels in a narrow MIUI freeform window.
old_tabs='ScrollableTabRow(selectedTabIndex=tab,containerColor=Bg,edgePadding=0.dp){listOf("Overview","Session","Charts","AI","History","Safety","Logs").forEachIndexed{i,n->Tab(selected=tab==i,onClick={tab=i},text={Text(n)})}}'
assert old_tabs in ms,'R28 tab anchor missing'
ms=ms.replace(old_tabs,'ResponsiveTabs(tab){tab=it}',1)

insert='@Composable fun Overview(s:RuntimeState)'
assert insert in ms,'R28 Overview anchor missing'
responsive='''@Composable fun ResponsiveTabs(selected:Int,onSelect:(Int)->Unit){\n    val names=listOf("Overview","Session","Charts","AI","History","Safety","Logs")\n    BoxWithConstraints(Modifier.fillMaxWidth()){\n        if(maxWidth < 560.dp){\n            Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(2.dp)){\n                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(2.dp)){\n                    names.take(4).forEachIndexed{i,n->TextButton(onClick={onSelect(i)},modifier=Modifier.weight(1f)){Text(n,color=if(selected==i)Green else Muted,maxLines=1)}}\n                }\n                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(2.dp)){\n                    names.drop(4).forEachIndexed{j,n->val i=j+4;TextButton(onClick={onSelect(i)},modifier=Modifier.weight(1f)){Text(n,color=if(selected==i)Green else Muted,maxLines=1)}}\n                }\n            }\n        }else{\n            ScrollableTabRow(selectedTabIndex=selected,containerColor=Bg,edgePadding=0.dp){names.forEachIndexed{i,n->Tab(selected=selected==i,onClick={onSelect(i)},text={Text(n)})}}\n        }\n    }\n}\n\n'''
ms=ms.replace(insert,responsive+insert,1)

# The legacy PERFORMANCE card is session-CSV-bound and shows all dashes while the
# live hardware row above is already valid. Replace the duplicate with explicit
# session truth so an inactive detector never looks like a hardware-read failure.
perf_pat=re.compile(r'BoxCard\("PERFORMANCE","Little: \.?\$\{positiveLongText\(s\.telemetry\.littleKhz,1000," MHz"\)\}.*?P95/P99: \$\{positiveText\(s\.telemetry\.p95," ms"\)\} / \$\{positiveText\(s\.telemetry\.p99," ms"\)\}"\);')
match=perf_pat.search(ms)
if not match:
    exact='BoxCard("PERFORMANCE","Little: ${positiveLongText(s.telemetry.littleKhz,1000," MHz")}\\nBig: ${positiveLongText(s.telemetry.bigKhz,1000," MHz")}\\nGPU: ${positiveLongText(s.telemetry.gpuHz,1_000_000," MHz")}\\nProfile: ${s.telemetry.profile}\\nP95/P99: ${positiveText(s.telemetry.p95," ms")} / ${positiveText(s.telemetry.p99," ms")}");'
    assert exact in ms,'R28 PERFORMANCE anchor missing'
    ms=ms.replace(exact,'SessionPerformanceCard(s);',1)
else:
    ms=ms[:match.start()]+'SessionPerformanceCard(s);'+ms[match.end():]

power_old='BoxCard("POWER","${s.telemetry.batteryStatus} • $power\\n$current • $voltage\\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})");'
assert power_old in ms,'R28 POWER anchor missing'
power_new='BoxCard("POWER",if(s.telemetry.powerValid=="1"||s.telemetry.powerValid.equals("true",true))"${s.telemetry.batteryStatus} • $power\\n$current • $voltage\\nValidity: ${s.telemetry.powerValid} (${s.telemetry.powerReason})" else "Waiting for a valid active-session power sample.\\nReason: ${s.telemetry.powerReason.ifBlank{\"NOT_PUBLISHED\"}}");'
ms=ms.replace(power_old,power_new,1)

card_anchor='@Composable fun StatusCard(s:RuntimeState)'
assert card_anchor in ms,'R28 StatusCard anchor missing'
perf_fn='''@Composable fun SessionPerformanceCard(s:RuntimeState){\n    val live=s.active=="1"&&s.sampleFresh\n    val body=if(live)\n        "Profile: ${s.telemetry.profile}\\nFPS: ${positiveText(s.telemetry.fps,\"\")} • Frame: ${positiveText(s.telemetry.frameMs,\" ms\")} • Jank: ${if(s.telemetry.jank>=0)\"%.1f%%\".format(s.telemetry.jank) else \"—\"}\\nP95/P99: ${positiveText(s.telemetry.p95,\" ms\")} / ${positiveText(s.telemetry.p99,\" ms\")}"\n    else "Waiting for an active DJAEGER game session. Live CPU/GPU clocks and temperatures remain available above and are not treated as session telemetry."\n    BoxCard("SESSION PERFORMANCE",body)\n}\n\n'''
ms=ms.replace(card_anchor,perf_fn+card_anchor,1)

m.write_text(ms)
M=m.read_text(); B=b.read_text()
checks={
 'R28_VERSION':'0.12.1-r28' in B and 'v0.12.1-r28 • LIVE HARDWARE' in M,
 'RESPONSIVE_TABS':'@Composable fun ResponsiveTabs' in M and 'if(maxWidth < 560.dp)' in M and 'ResponsiveTabs(tab){tab=it}' in M,
 'ALL_TABS_PRESERVED':all(x in M for x in ['"Overview"','"Session"','"Charts"','"AI"','"History"','"Safety"','"Logs"']),
 'STALE_PERFORMANCE_REMOVED':'BoxCard("PERFORMANCE","Little:' not in M,
 'SESSION_PERFORMANCE_TRUTH':'BoxCard("SESSION PERFORMANCE",body)' in M and 's.active=="1"&&s.sampleFresh' in M,
 'POWER_INVALID_TRUTH':'Waiting for a valid active-session power sample.' in M,
 'R27_LIVE_HARDWARE_PRESERVED':all(x in M for x in ['LiveClockRow()','Thermal("CPU TEMP",f.cpuT.toInt()','Thermal("GPU TEMP",f.gpuT.toInt()','Thermal("SKIN",f.skinT.toInt()','Thermal("BATTERY",f.batT.toInt()']),
 'MODULE_VAULT_PRESERVED':'GEMINI KEY VAULT • MODULE TRUTH' in M,
 'RUNTIME_IDENTITY_PRESERVED':'RUNTIME IDENTITY' in M,
}
for k,v in checks.items(): print(f'{k}={"PASS" if v else "FAIL"}')
bad=[k for k,v in checks.items() if not v]; assert not bad,','.join(bad)
print('R28_FREEFORM_NAV=COMPACT_TWO_ROW')
print('R28_SESSION_CARDS=NO_FALSE_HARDWARE_FAILURE')
