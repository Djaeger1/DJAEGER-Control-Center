from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); b=build.read_text()

# GAMEREG1 is additive to the validated LOOPFIX1 CCMATCH1 UI. Keep protocol/versionCode.
assert 'versionCode = 12258' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-ccmatch1"' in b
b=b.replace('versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-ccmatch1"','versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1"',1)

# Repository model and trusted, on-demand root bridge. Inputs travel on stdin and are
# validated again by the module helper; no package/name is interpolated into a shell command.
anchor='data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false)\n'
assert anchor in r
r=r.replace(anchor,anchor+'data class GameRegistryEntry(val type:String,val packageName:String,val displayName:String)\n',1)

methods=r'''
    suspend fun gameRegistryList():Pair<Boolean,List<GameRegistryEntry>> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/system/bin/djaeger-game-registry list",5000)
        if(rc!=0) return@withContext Pair(false,emptyList())
        val rows=out.lineSequence().mapNotNull{line->
            val p=line.split('|',limit=3)
            if(p.size==3&&(p[0]=="BUILTIN"||p[0]=="MANUAL")&&p[1].isNotBlank()) GameRegistryEntry(p[0],p[1],p[2].ifBlank{p[1]}) else null
        }.toList()
        Pair(true,rows)
    }

    suspend fun addManualGame(packageName:String,displayName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        val name=displayName.replace('\n',' ').replace('\r',' ').replace('\t',' ').trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        if(name.isBlank()||name.toByteArray().size>120) return@withContext Pair(false,"Nama game kosong atau terlalu panjang")
        val (rc,out)=suStdin("$module/system/bin/djaeger-game-registry add-stdin",pkg+"\n"+name,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=ADDED" else "STATUS=FAILED"})
    }

    suspend fun removeManualGame(packageName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        val (rc,out)=suStdin("$module/system/bin/djaeger-game-registry remove-stdin",pkg,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=REMOVED" else "STATUS=FAILED"})
    }

'''
anchor='    private fun parseTelemetry(line: String): Telemetry {'
assert anchor in r
r=r.replace(anchor,methods+anchor,1)

# Header identity and Session access to repository.
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1' in m
m=m.replace('CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1','CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1',1)
assert '1->Session(state,samples);' in m
m=m.replace('1->Session(state,samples);','1->Session(state,samples,repo);',1)
assert '@Composable fun Session(s:RuntimeState,samples:List<Sample>){' in m
m=m.replace('@Composable fun Session(s:RuntimeState,samples:List<Sample>){','@Composable fun Session(s:RuntimeState,samples:List<Sample>,repo:DjaegerRepository){',1)

card=r'''@Composable fun GameRegistryCard(repo:DjaegerRepository){
    val scope=rememberCoroutineScope()
    var gameName by remember{mutableStateOf("")}
    var packageName by remember{mutableStateOf("")}
    var entries by remember{mutableStateOf<List<GameRegistryEntry>>(emptyList())}
    var status by remember{mutableStateOf("Siap. Game manual memakai detector DJAEGER yang sama dengan game bawaan.")}
    var busy by remember{mutableStateOf(false)}
    var refreshToken by remember{mutableIntStateOf(0)}

    LaunchedEffect(refreshToken){
        busy=true
        val (ok,list)=repo.gameRegistryList()
        if(ok){entries=list;if(refreshToken==0)status="Registry siap • ${list.count{it.type=="MANUAL"}} game manual"}
        else status="Registry belum tersedia. Pastikan modul GAMEREG1 terpasang."
        busy=false
    }

    Column(Modifier.fillMaxWidth().background(Card, RoundedCornerShape(14.dp)).padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){
        Text("GAME REGISTRY • MANUAL",fontWeight=FontWeight.Bold)
        Text("Tambahkan game baru tanpa rebuild modul. Package harus sudah terpasang. Game manual masuk ke session detector, frame observer, Gemini/Hermes, Agent, readback dan learning yang sama.",color=Muted,style=MaterialTheme.typography.bodySmall)
        OutlinedTextField(value=gameName,onValueChange={gameName=it},label={Text("Nama game")},placeholder={Text("Contoh: Game Baru")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        OutlinedTextField(value=packageName,onValueChange={packageName=it},label={Text("Package name")},placeholder={Text("com.developer.game")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={
                scope.launch{
                    busy=true
                    val (ok,msg)=repo.addManualGame(packageName,gameName)
                    status=msg.replace("\n"," • ")
                    if(ok){gameName="";packageName="";refreshToken++}else busy=false
                }
            },enabled=!busy&&gameName.isNotBlank()&&packageName.isNotBlank(),modifier=Modifier.weight(1f)){Text(if(busy)"PROSES…" else "TAMBAH GAME")}
            OutlinedButton(onClick={refreshToken++},enabled=!busy){Text("REFRESH")}
        }
        Text(status,color=if(status.contains("REJECTED")||status.contains("tidak valid")||status.contains("belum tersedia")) Red else Muted,style=MaterialTheme.typography.bodySmall)
        if(entries.isNotEmpty()){
            HorizontalDivider()
            entries.forEach{e->
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                    Column(Modifier.weight(1f)){
                        Text(e.displayName,fontWeight=FontWeight.SemiBold)
                        Text(e.packageName,color=Muted,style=MaterialTheme.typography.bodySmall)
                        Text(if(e.type=="BUILTIN")"BAWAAN • terkunci" else "MANUAL • dapat dihapus",color=Muted,style=MaterialTheme.typography.labelSmall)
                    }
                    if(e.type=="MANUAL") TextButton(onClick={scope.launch{busy=true;val (ok,msg)=repo.removeManualGame(e.packageName);status=msg.replace("\n"," • ");if(ok)refreshToken++ else busy=false}},enabled=!busy){Text("HAPUS")}
                }
            }
        }
    }
}

'''
anchor='@Composable fun Session(s:RuntimeState,samples:List<Sample>,repo:DjaegerRepository){'
assert anchor in m
m=m.replace(anchor,card+anchor,1)
# Put registry at top of Session without disturbing existing monitoring cards.
old='''    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("MONITOR SESSION"'''
new='''    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        GameRegistryCard(repo)
        BoxCard("MONITOR SESSION"'''
assert old in m
m=m.replace(old,new,1)

main.write_text(m); repo.write_text(r); build.write_text(b)

# Build-time invariants.
M=main.read_text(); R=repo.read_text(); B=build.read_text()
assert 'versionCode = 12258' in B and 'loopfix1-gamereg1' in B
assert 'GAME REGISTRY • MANUAL' in M
assert 'Nama game' in M and 'Package name' in M and 'TAMBAH GAME' in M and 'HAPUS' in M
assert '1->Session(state,samples,repo)' in M
assert 'djaeger-game-registry list' in R
assert 'djaeger-game-registry add-stdin' in R
assert 'djaeger-game-registry remove-stdin' in R
assert 'pkg+"\\n"+name' in R
assert 'ProcessBuilder("su"' in R
assert 'AGENT-FULL-HW-REBUILD3' not in M
print('GAMEREG1_CC_PATCH=PASS')
print('MANUAL_GAME_INPUT=NAME+PACKAGE')
print('TRUSTED_STDIN_BRIDGE=PASS')
print('CONTROL_CENTER_VC=12258')
print('NEW_RECURRING_ROOT_READS=0')
