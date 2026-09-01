#!/usr/bin/env python3
from pathlib import Path
import re

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()

old='@Composable fun App(){val repo=remember{DjaegerRepository()};val context=androidx.compose.ui.platform.LocalContext.current;val notifier=remember{BugNotifier(context)};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()}'
new='@Composable fun App(){val repo=remember{DjaegerRepository()};val context=androidx.compose.ui.platform.LocalContext.current;val notifier=remember{BugNotifier(context)};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()};var manualRefresh by remember{mutableIntStateOf(0)};var refreshBusy by remember{mutableStateOf(false)};var refreshStatus by remember{mutableStateOf("LOCAL AUTO 1s")}'
if old not in s: raise SystemExit('R10_FAIL=App-anchor')
s=s.replace(old,new,1)

anchor='    LaunchedEffect(lifecycleOwner){lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){while(true){state=repo.snapshot();notifier.notifyIfNeeded(state.bugHealth);if(state.root&&state.installed&&state.sampleFresh){with(state.telemetry){samples.add(Sample(if(fps>0)fps else Double.NaN,if(frameMs>0)frameMs else Double.NaN,sampleTemp(cpuT),sampleTemp(gpuT),sampleTemp(skinT),sampleTemp(batT)));while(samples.size>60)samples.removeAt(0)}};delay(1000)}}}'
if anchor not in s: raise SystemExit('R10_FAIL=poll-anchor')
extra=anchor+'\n    LaunchedEffect(manualRefresh){if(manualRefresh>0){refreshBusy=true;val before=state.updated;val fresh=repo.snapshot();state=fresh;notifier.notifyIfNeeded(fresh.bugHealth);val now=SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date());refreshStatus=if(fresh.error.isNotBlank()) "LOCAL REFRESH ERROR • $now" else if(fresh.updated>0&&fresh.updated==before) "LOCAL UNCHANGED • $now" else "LOCAL UPDATED • $now";refreshBusy=false}}'
s=s.replace(anchor,extra,1)

# Do not depend on a generated-version header. r7/r9 transforms may change it.
pat=r'MaterialTheme\(colorScheme=darkColorScheme\(primary=Green,background=Bg,surface=Card\)\)\{Column\(Modifier\.fillMaxSize\(\)\.background\(Bg\)\.padding\(16\.dp\)\)\{Text\("DJAEGER",fontWeight=FontWeight\.Black,style=MaterialTheme\.typography\.headlineMedium\);Text\("CONTROL CENTER • [^"]+",color=Muted\);Spacer\(Modifier\.height\(12\.dp\)\);ScrollableTabRow'
replacement='MaterialTheme(colorScheme=darkColorScheme(primary=Green,background=Bg,surface=Card)){Column(Modifier.fillMaxSize().background(Bg).padding(16.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Column(Modifier.weight(1f)){Text("DJAEGER",fontWeight=FontWeight.Black,style=MaterialTheme.typography.headlineMedium);Text("CONTROL CENTER • v0.12.1-r10 • LOCAL REALTIME 1s",color=Muted);Text(refreshStatus,color=Muted,style=MaterialTheme.typography.labelSmall)};Button(onClick={if(!refreshBusy)manualRefresh++},enabled=!refreshBusy){Text(if(refreshBusy)"REFRESHING…" else "REFRESH LOCAL")}};Spacer(Modifier.height(12.dp));ScrollableTabRow'
s,n=re.subn(pat,replacement,s,count=1)
if n!=1: raise SystemExit('R10_FAIL=header-anchor')

# Clarify that Gemini status is cached local state; manual refresh never calls Gemini.
# Patch any visible Gemini key status title if present after generated baseline.
s=s.replace('"GEMINI KEY STATUS"','"GEMINI KEY STATUS • CACHED LOCAL RECORD"')

p.write_text(s)
print('R10_MANUAL_REFRESH_INTEGRATION=PASS')
print('R10_REFRESH_TRANSPORT=LOCAL_SNAPSHOT_ONLY')
