from pathlib import Path
import re, hashlib

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); b=build.read_text()

def fun_block(src, name):
    key='@Composable fun '+name
    start=src.index(key)
    op=src.index('{', start)
    depth=0
    i=op
    in_str=False
    esc=False
    while i < len(src):
        c=src[i]
        if in_str:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': in_str=False
        else:
            if c=='"': in_str=True
            elif c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0:
                    return start, i+1, src[start:i+1]
        i+=1
    raise RuntimeError('unterminated '+name)

# Preserve the user's existing GAME registry card byte-for-byte.
gs,ge,game_before=fun_block(m,'GameRegistryCard')
game_hash=hashlib.sha256(game_before.encode()).hexdigest()

# Pair identity only; Overview/layout/order outside APP registry is intentionally untouched.
if 'versionCode = 12261' in b:
    b=b.replace('versionCode = 12261','versionCode = 12262',1)
if 'versionName = ' in b and 'dualreg3-manualapp1' not in b:
    b=re.sub(r'versionName = "([^"]+)"',lambda x:'versionName = "'+x.group(1)+'-dualreg3-manualapp1"',b,count=1)

# Add explicit APP-registry model beside the existing GAME model.
if 'data class AppRegistryEntry(' not in r:
    anchor='data class GameRegistryEntry(val type:String,val packageName:String,val displayName:String)\n'
    assert anchor in r
    r=r.replace(anchor,anchor+'data class AppRegistryEntry(val type:String,val packageName:String,val displayName:String)\n',1)

# Dedicated APP bridge. It never uses the GAME add command and never auto-classifies a package.
if 'suspend fun appRegistryList()' not in r:
    methods=r'''
    suspend fun appRegistryList():Pair<Boolean,List<AppRegistryEntry>> = withContext(Dispatchers.IO){
        val (rc,out)=su("$module/system/bin/djaeger-app-registry list",5000)
        if(rc!=0) return@withContext Pair(false,emptyList())
        val rows=out.lineSequence().mapNotNull{line->
            val p=line.split('|',limit=3)
            if(p.size==3&&p[0]=="MANUAL"&&p[1].isNotBlank()) AppRegistryEntry(p[0],p[1],p[2].ifBlank{p[1]}) else null
        }.toList()
        Pair(true,rows)
    }

    suspend fun addManualApp(packageName:String,displayName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        val name=displayName.replace('\n',' ').replace('\r',' ').replace('\t',' ').trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        if(name.isBlank()||name.toByteArray().size>120) return@withContext Pair(false,"Nama aplikasi kosong atau terlalu panjang")
        val (rc,out)=suStdin("$module/system/bin/djaeger-app-registry add-stdin",pkg+"\n"+name,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=ADDED" else "STATUS=FAILED"})
    }

    suspend fun removeManualApp(packageName:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val pkg=packageName.trim()
        if(!Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$").matches(pkg)) return@withContext Pair(false,"Package name tidak valid")
        val (rc,out)=suStdin("$module/system/bin/djaeger-app-registry remove-stdin",pkg,7000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"STATUS=REMOVED" else "STATUS=FAILED"})
    }

'''
    anchor='    private fun parseTelemetry(line: String): Telemetry {'
    assert anchor in r
    r=r.replace(anchor,methods+anchor,1)

# Replace only the old read-only APP-registry card. GAME card is left untouched.
as_,ae,old_app=fun_block(m,'AppRegistryListCard')
new_app=r'''@Composable fun AppRegistryListCard(repo:DjaegerRepository){
    val scope=rememberCoroutineScope()
    var appName by remember{mutableStateOf("")}
    var packageName by remember{mutableStateOf("")}
    var entries by remember{mutableStateOf<List<AppRegistryEntry>>(emptyList())}
    var status by remember{mutableStateOf("Siap. Hanya aplikasi yang Anda tambahkan masuk jalur APP efficiency.")}
    var busy by remember{mutableStateOf(false)}
    var refreshToken by remember{mutableIntStateOf(0)}

    LaunchedEffect(refreshToken){
        busy=true
        val (ok,list)=repo.appRegistryList()
        if(ok){entries=list;if(refreshToken==0)status="Registry siap • ${list.size} aplikasi manual"}
        else status="Registry APP belum tersedia. Pastikan modul DUALREG3 terpasang."
        busy=false
    }

    Column(Modifier.fillMaxWidth().background(Card, RoundedCornerShape(14.dp)).padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){
        Text("APP REGISTRY • MANUAL",fontWeight=FontWeight.Bold)
        Text("Tambahkan aplikasi biasa secara manual. APP memakai jalur efisiensi baterai/thermal/UI responsiveness dan tidak menerima game semantics, game FPS target, atau game boost policy.",color=Muted,style=MaterialTheme.typography.bodySmall)
        OutlinedTextField(value=appName,onValueChange={appName=it},label={Text("Nama aplikasi")},placeholder={Text("Contoh: Facebook")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        OutlinedTextField(value=packageName,onValueChange={packageName=it},label={Text("Package name")},placeholder={Text("com.developer.app")},singleLine=true,modifier=Modifier.fillMaxWidth(),enabled=!busy)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={
                scope.launch{
                    busy=true
                    val (ok,msg)=repo.addManualApp(packageName,appName)
                    status=msg.replace("\n"," • ")
                    if(ok){appName="";packageName="";refreshToken++}else busy=false
                }
            },enabled=!busy&&appName.isNotBlank()&&packageName.isNotBlank(),modifier=Modifier.weight(1f)){Text(if(busy)"PROSES…" else "TAMBAH APP")}
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
                        Text("MANUAL • APP_EFFICIENCY • dapat dihapus",color=Muted,style=MaterialTheme.typography.labelSmall)
                    }
                    TextButton(onClick={scope.launch{busy=true;val (ok,msg)=repo.removeManualApp(e.packageName);status=msg.replace("\n"," • ");if(ok)refreshToken++ else busy=false}},enabled=!busy){Text("HAPUS")}
                }
            }
        }
    }
}'''
m=m[:as_]+new_app+m[ae:]

# Existing call stays at its existing location/order; only pass repo instead of snapshot state.
m=m.replace('AppRegistryListCard(s)','AppRegistryListCard(repo)')

# Verify GAME card did not change.
gs2,ge2,game_after=fun_block(m,'GameRegistryCard')
assert hashlib.sha256(game_after.encode()).hexdigest()==game_hash

main.write_text(m); repo.write_text(r); build.write_text(b)

M=main.read_text(); R=repo.read_text(); B=build.read_text()
assert 'GAME REGISTRY • MANUAL' in M and 'Nama game' in M and 'TAMBAH GAME' in M
assert 'APP REGISTRY • MANUAL' in M and 'Nama aplikasi' in M and 'TAMBAH APP' in M
assert 'AppRegistryListCard(repo)' in M
assert 'djaeger-app-registry list' in R
assert 'djaeger-app-registry add-stdin' in R
assert 'djaeger-app-registry remove-stdin' in R
assert 'djaeger-game-registry add-stdin' in R
assert 'versionCode = 12262' in B
assert 'dualreg3-manualapp1' in B
print('DUALREG3_MANUAL_APP1=PASS')
print('GAME_REGISTRY_UI_UNCHANGED=PASS')
print('APP_REGISTRY_UI=MANUAL_NAME_PACKAGE_ADD_REFRESH_REMOVE')
print('APP_AND_GAME_COMMAND_PATHS=SEPARATE')
print('CONTROL_CENTER_VC=12262')
