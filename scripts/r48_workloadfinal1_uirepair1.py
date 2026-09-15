from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

m=main.read_text()
r=repo.read_text()

# ---------------------------------------------------------------------------
# 1) ENGINE / SESSION: workload-aware display only.
#    GAME authority remains exactly where it already lives; APP/SYSTEM are
#    displayed as observe-only instead of the misleading WAITING GAME label.
# ---------------------------------------------------------------------------
start=m.index('@Composable fun StatusCard(s:RuntimeState)')
end=m.index('@Composable fun ThermalRow',start)
status=r'''@Composable fun StatusCard(s:RuntimeState){
    val stale=runtimeStateStale(s)
    val engine=if(stale) "STALE" else "LIVE"
    val workloadClass=envField(s.workloadContext,"WORKLOAD_CLASS").ifBlank{"UNKNOWN"}
    val workloadPackage=envField(s.workloadContext,"PACKAGE").ifBlank{"UNKNOWN"}
    val workloadProfile=envField(s.workloadContext,"WORKLOAD_PROFILE").ifBlank{"UNKNOWN"}
    val sessionState=when{
        stale->"UNKNOWN / STALE"
        workloadClass=="APP"->"APP ACTIVE • OBSERVE ONLY"
        workloadClass=="SYSTEM"->"SYSTEM ACTIVE • OBSERVE ONLY"
        workloadClass=="GAME"&&s.active=="1"->"GAME ACTIVE"
        s.active=="1"->"GAME ACTIVE"
        else->"WAITING GAME"
    }
    val sample=when{s.telemetry.epoch>0->SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(Date(s.telemetry.epoch*1000));s.sampleFresh->"LIVE SYSFS";else->"—"}
    val game=if(s.active=="1") s.game else if(stale) "—" else "NA"
    val window=if(s.active=="1") s.window else if(stale) "—" else "INACTIVE"
    val profile=when{
        s.active=="1"->s.telemetry.profile
        workloadClass=="APP"||workloadClass=="SYSTEM"->workloadProfile
        else->"—"
    }
    val execution=if(s.active=="1"&&workloadClass=="GAME") "ACTIVE" else "BLOCKED / OBSERVE ONLY"
    val age=if(s.updated>0) (System.currentTimeMillis()/1000-s.updated).coerceAtLeast(0) else -1
    val ageText=if(age>=0) "${age}s" else "—"
    val body=if(s.installed) "Engine: $engine • age $ageText\nSession: $sessionState\nModule: ${s.moduleVersion}\nGame: $game\nWindow: $window\nProfile: $profile\nWorkload: $workloadClass • $workloadPackage\nGame execution: $execution\nLast device sample: $sample\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found"
    BoxCard("ENGINE / SESSION",body)
}
'''
m=m[:start]+status+'\n'+m[end:]

# ---------------------------------------------------------------------------
# 2) APP registry is a real first-class list/editor, separate from GAME.
#    All mutations are explicit user actions; no automatic background writes.
# ---------------------------------------------------------------------------
if 'data class AppRegistryEntry(' not in r:
    anchor='data class GameRegistryEntry(val type:String,val packageName:String,val displayName:String)'
    assert anchor in r, 'GameRegistryEntry anchor missing'
    r=r.replace(anchor,anchor+'\ndata class AppRegistryEntry(val packageName:String,val profile:String,val displayName:String)',1)

repo_anchor='    suspend fun gameRegistryList():Pair<Boolean,List<GameRegistryEntry>> = withContext(Dispatchers.IO){'
assert repo_anchor in r, 'gameRegistryList anchor missing'
app_methods=r'''    suspend fun addManualApp(packageName:String,displayName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        val name=displayName.replace('\n',' ').replace('\r',' ').replace('\t',' ').trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        if(name.isBlank()||name.toByteArray().size>120) return@withContext Pair(false,"Nama aplikasi kosong atau terlalu panjang")
        if(pkg in setOf("sts.al","com.levelinfinite.gst","com.garena.game.kgid")) return@withContext Pair(false,"STATUS=REJECTED\nREASON=BUILTIN_GAME")
        val cmd="""
            P=/data/adb/djaeger_ai
            APP=\"\$P/workload/app_registry.tsv\"
            GAME=\"\$P/custom_games.tsv\"
            mkdir -p \"\$P/workload\" || exit 30
            IFS= read -r pkg || exit 31
            IFS= read -r profile || exit 32
            IFS= read -r name || exit 33
            case \"\$pkg\" in sts.al|com.levelinfinite.gst|com.garena.game.kgid) echo STATUS=REJECTED; echo REASON=BUILTIN_GAME; exit 40;; esac
            atmp=\"\$APP.cc.\$\$\"; : >\"\$atmp\" || exit 41
            [ -r \"\$APP\" ] && awk -F '\\t' -v p=\"\$pkg\" '\$1!=p' \"\$APP\" >\"\$atmp\"
            printf '%s\\t%s\\t%s\\n' \"\$pkg\" \"\$profile\" \"\$name\" >>\"\$atmp\" || exit 42
            chmod 600 \"\$atmp\" 2>/dev/null
            mv -f \"\$atmp\" \"\$APP\" || exit 43
            if [ -f \"\$GAME\" ]; then
              gtmp=\"\$GAME.cc.\$\$\"; awk -F '\\t' -v p=\"\$pkg\" '\$1!=p' \"\$GAME\" >\"\$gtmp\" || exit 44
              chmod 600 \"\$gtmp\" 2>/dev/null; mv -f \"\$gtmp\" \"\$GAME\" || exit 45
            fi
            CLASS=\"\$P/workload/bin/djaeger-workload-classifier\"
            [ -x \"\$CLASS\" ] && sh \"\$CLASS\" publish >/dev/null 2>&1 || true
            echo STATUS=ADDED
            echo CLASS=APP
        """.trimIndent()
        val (rc,out)=suStdin(cmd,pkg+"\nAPP_INTERACTIVE\n"+name,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=ADDED" else "STATUS=FAILED"})
    }

    suspend fun removeManualApp(packageName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        val cmd="""
            P=/data/adb/djaeger_ai
            APP=\"\$P/workload/app_registry.tsv\"
            IFS= read -r pkg || exit 31
            [ -f \"\$APP\" ] || { echo STATUS=REMOVED; exit 0; }
            tmp=\"\$APP.cc.\$\$\"; awk -F '\\t' -v p=\"\$pkg\" '\$1!=p' \"\$APP\" >\"\$tmp\" || exit 41
            chmod 600 \"\$tmp\" 2>/dev/null; mv -f \"\$tmp\" \"\$APP\" || exit 42
            CLASS=\"\$P/workload/bin/djaeger-workload-classifier\"
            [ -x \"\$CLASS\" ] && sh \"\$CLASS\" publish >/dev/null 2>&1 || true
            echo STATUS=REMOVED
        """.trimIndent()
        val (rc,out)=suStdin(cmd,pkg,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=REMOVED" else "STATUS=FAILED"})
    }

'''
r=r.replace(repo_anchor,app_methods+repo_anchor,1)

# Parse the already consolidated APP registry snapshot; no extra recurring root read.
insert_before='@Composable fun GameRegistryCard(repo:DjaegerRepository)'
assert insert_before in m, 'GameRegistryCard anchor missing'
app_card=r'''private fun parseAppRegistry(raw:String):List<AppRegistryEntry> = raw.lineSequence().mapNotNull{line->
    val p=line.trim().split('\t',limit=3)
    if(p.size>=2&&p[0].isNotBlank()) AppRegistryEntry(p[0],p[1].ifBlank{"APP_INTERACTIVE"},p.getOrNull(2)?.ifBlank{p[0]}?:p[0]) else null
}.toList()

@Composable fun AppRegistryCard(s:RuntimeState,repo:DjaegerRepository){
    val scope=rememberCoroutineScope()
    var appName by remember{mutableStateOf("")}
    var packageName by remember{mutableStateOf("")}
    var status by remember{mutableStateOf("Siap. APP diamati DJAEGER tanpa menerima kebijakan hardware game.")}
    var busy by remember{mutableStateOf(false)}
    val entries=remember(s.appRegistry){parseAppRegistry(s.appRegistry)}

    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){
        Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){
            Text("APP REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)
            Text("Aplikasi umum dipisahkan dari GAME registry. APP tetap bisa dipahami/diamati, tetapi game execution tetap diblokir.",color=Muted)
            OutlinedTextField(value=appName,onValueChange={appName=it},label={Text("Nama aplikasi")},singleLine=true,modifier=Modifier.fillMaxWidth())
            OutlinedTextField(value=packageName,onValueChange={packageName=it},label={Text("Package name")},singleLine=true,modifier=Modifier.fillMaxWidth())
            Button(onClick={
                if(!busy){busy=true;scope.launch{val x=repo.addManualApp(packageName,appName);status=x.second;if(x.first){appName="";packageName=""};busy=false}}
            },enabled=!busy&&appName.isNotBlank()&&packageName.isNotBlank(),modifier=Modifier.fillMaxWidth()){Text(if(busy)"MEMPROSES…" else "TAMBAH APP")}
            Text(status,color=if(status.contains("REJECTED")||status.contains("FAILED")||status.contains("tidak valid")) Red else Muted)
            HorizontalDivider(color=Muted.copy(alpha=.35f))
            Text("APP LIST • ${entries.size}",color=Green,fontWeight=FontWeight.Bold)
            if(entries.isEmpty()) Text("Belum ada APP manual.",color=Muted)
            entries.forEach{e->
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){
                    Column(Modifier.weight(1f)){
                        Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)
                        Text(e.packageName,color=Muted,style=MaterialTheme.typography.bodySmall)
                        Text("${e.profile} • OBSERVE ONLY",color=Muted,style=MaterialTheme.typography.bodySmall)
                    }
                    TextButton(onClick={if(!busy){busy=true;scope.launch{val x=repo.removeManualApp(e.packageName);status=x.second;busy=false}}},enabled=!busy){Text("HAPUS")}
                }
            }
        }
    }
}

'''
m=m.replace(insert_before,app_card+insert_before,1)

# ---------------------------------------------------------------------------
# 3) Session layout: summary -> APP list -> GAME list -> existing monitoring.
#    Keep every monitoring card and statistic that existed before WORKLOADFINAL1.
# ---------------------------------------------------------------------------
sess_start=m.index('@Composable fun Session(s:RuntimeState,samples:List<Sample>,repo:DjaegerRepository)')
sess_end=m.index('private fun monitorPhase',sess_start)
new_session=r'''@Composable fun Session(s:RuntimeState,samples:List<Sample>,repo:DjaegerRepository){
    val fps=samples.map{it.fps}.filter{it.isFinite()&&it>0};val frame=samples.map{it.frame}.filter{it.isFinite()&&it>0};val cpu=samples.map{it.cpu.toDouble()}.filter{it.isFinite()&&it>=0};val gpu=samples.map{it.gpu.toDouble()}.filter{it.isFinite()&&it>=0};val skin=samples.map{it.skin.toDouble()}.filter{it.isFinite()&&it>=0}
    val phase=monitorPhase(s)
    val anomalies=anomalySummary(s,samples)
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        DualRegistrySummaryCard(s)
        AppRegistryCard(s,repo)
        GameRegistryCard(repo)
        BoxCard("MONITOR SESSION","Samples: ${samples.size} / 60\nWindow: ${s.window} • Game: ${s.game}\nObserved phase: $phase\nThis phase is a monitor-side interpretation, not a command to DJAEGER.")
        BoxCard("60-SECOND STATISTICS","FPS avg/min/max: ${stat3(fps,"")}\nFrame avg/peak: ${stat2(frame," ms")}\nCPU avg/peak: ${stat2(cpu,"°C")}\nGPU avg/peak: ${stat2(gpu,"°C")}\nSkin avg/peak: ${stat2(skin,"°C")}")
        BoxCard("ANOMALY WATCH",anomalies)
        BoxCard("CURRENT INTERPRETATION",humanDecision(s))
    }
}
'''
m=m[:sess_start]+new_session+'\n'+m[sess_end:]

# Explicit colors for the GAME registry dark card and its entry names.
m=m.replace('Text("GAME REGISTRY • MANUAL",fontWeight=FontWeight.Bold)','Text("GAME REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)')
m=m.replace('Text(e.displayName,fontWeight=FontWeight.SemiBold)','Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)')

main.write_text(m)
repo.write_text(r)

# ---------------------------------------------------------------------------
# 4) Regression gates: fail the build if any reported regression comes back.
# ---------------------------------------------------------------------------
M=main.read_text(); R=repo.read_text()
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('private fun compactModuleVersion',M.index('@Composable fun Overview(s:RuntimeState)'))]
expected=[
    'StatusCard(s)','ThoughtsCard(s)','Metric("FPS"','ThermalRow(s)','NetworkCard(s.network)','StrategyCard(s)',
    'AgentRebuild3Card(s)','HermesCloudCard(s)','KernelAgentSyncCard(s)','HermesCard(s)','HumanComfortHcc1Card(s)',
    'ContextVNextCard(s)','MemoryVNextCard(s)','ReasoningV2Card(s)','SkillsVNextCard(s)','LearningResearchV2Card(s)',
    'OutcomeLearningCard(s)','StrategyCompositionCard(s)','DecisionPipelineCard(s)','BoxCard("PERFORMANCE"','BoxCard("POWER"',
    'BoxCard("FRAME INTELLIGENCE • RECENT"','WorkloadIntelligenceCard(s)'
]
pos=[ov.index(x) for x in expected]
assert pos==sorted(pos),pos
assert ov.count('WorkloadIntelligenceCard(s)')==1
assert 'StatusCard(s);ThoughtsCard(s);' in ov
assert 'StatusCard(s);WorkloadIntelligenceCard(s);' not in ov
assert 'APP ACTIVE • OBSERVE ONLY' in M
assert 'SYSTEM ACTIVE • OBSERVE ONLY' in M
assert '@Composable fun AppRegistryCard(s:RuntimeState,repo:DjaegerRepository)' in M
assert 'APP REGISTRY • MANUAL' in M and 'APP LIST • ${entries.size}' in M
assert 'DualRegistrySummaryCard(s)\n        AppRegistryCard(s,repo)\n        GameRegistryCard(repo)' in M
assert 'Text("GAME REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)' in M
assert 'Text(e.displayName,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)' in M
assert 'suspend fun addManualApp' in R and 'suspend fun removeManualApp' in R
assert 'APP_INTERACTIVE' in R and 'REASON=BUILTIN_GAME' in R
assert '/sys/' not in app_methods and '/proc/sys/' not in app_methods

print('UIREPAIR1=PASS')
print('OVERVIEW_ESTABLISHED_ORDER=PRESERVED')
print('WORKLOAD_CARD=ADDITIVE_AT_END')
print('SESSION_WORKLOAD_STATUS=FIXED')
print('APP_REGISTRY_LIST=VISIBLE_EDITABLE')
print('GAME_REGISTRY_LIST=VISIBLE_READABLE')
print('DUAL_REGISTRY_MUTATION=EXPLICIT_USER_ACTION_ONLY')
print('DIRECT_HARDWARE_WRITE=NONE')
