from pathlib import Path
g=Path('app/build.gradle.kts'); s=g.read_text(); marker='    kotlinOptions { jvmTarget = "17" }'
if 'sourceCompatibility = JavaVersion.VERSION_17' not in s:
    s=s.replace(marker,'    compileOptions {\n        sourceCompatibility = JavaVersion.VERSION_17\n        targetCompatibility = JavaVersion.VERSION_17\n    }\n'+marker)
s=s.replace('versionCode = 8','versionCode = 13').replace('versionName = "0.5.3-rc-cogo"','versionName = "0.6.1-rc-ai-bridge"'); g.write_text(s)
r=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'); s=r.read_text()
s=s.replace('"__$a__\\n"','"__${a}__\\n"').replace('"__$b__\\n"','"__${b}__\\n"')
s=s.replace('val updated:Long=0,val moduleVersion:String="unknown"', 'val updated:Long=0,val userMode:String="AUTO",val moduleVersion:String="unknown"')
s=s.replace('updated=rt["updated_at"]?.toLongOrNull()?:0,moduleVersion=moduleVersion', 'updated=rt["updated_at"]?.toLongOrNull()?:0,userMode=rt["user_mode"]?:"AUTO",moduleVersion=moduleVersion')
old='    private fun parseTelemetry(line:String):Telemetry{val c=parseCsv(line);fun s(i:Int)=c.getOrNull(i)?.trim().orEmpty();return Telemetry(s(0).toLongOrNull()?:0,s(1).toIntOrNull()?:0,s(2).toIntOrNull()?:0,s(3).toIntOrNull()?:0,s(4).toIntOrNull()?:0,s(5).toLongOrNull()?:0,s(6).toLongOrNull()?:0,s(7).toLongOrNull()?:0,s(8),s(9).toDoubleOrNull()?:0.0,s(10).toDoubleOrNull()?:0.0,s(11).toDoubleOrNull()?:0.0,s(12).toDoubleOrNull()?:0.0,s(13).toDoubleOrNull()?:0.0,s(15),s(16).toLongOrNull()?:0,s(17).toLongOrNull()?:0,s(18).toDoubleOrNull()?:0.0,s(19),s(20),s(22))}'
new='''    private fun parseTelemetry(line: String): Telemetry {
    val c = parseCsv(line)
    fun field(i: Int): String = c.getOrNull(i)?.trim().orEmpty()
    return Telemetry(field(0).toLongOrNull()?:0,field(1).toIntOrNull()?:0,field(2).toIntOrNull()?:0,field(3).toIntOrNull()?:0,field(4).toIntOrNull()?:0,field(5).toLongOrNull()?:0,field(6).toLongOrNull()?:0,field(7).toLongOrNull()?:0,field(8),field(9).toDoubleOrNull()?:0.0,field(10).toDoubleOrNull()?:0.0,field(11).toDoubleOrNull()?:0.0,field(12).toDoubleOrNull()?:0.0,field(13).toDoubleOrNull()?:0.0,field(15),field(16).toLongOrNull()?:0,field(17).toLongOrNull()?:0,field(18).toDoubleOrNull()?:0.0,field(19),field(20),field(22))
}'''
if old not in s: raise SystemExit('parseTelemetry baseline not found')
s=s.replace(old,new)
insert='''
    suspend fun setUserMode(mode:String):Pair<Boolean,String> = withContext(Dispatchers.IO) {
        val normalized=mode.uppercase()
        val arg=when(normalized){"AUTO"->"auto";"DINGIN"->"dingin";"SEDANG"->"sedang";"HANGAT"->"hangat";"PANAS"->"panas";else->return@withContext Pair(false,"INVALID_MODE")}
        val (rc,out)=su("djaeger-ai mode $arg")
        Pair(rc==0,out.trim().ifBlank{if(rc==0) "REQUEST_SENT" else "MODE_COMMAND_FAILED"})
    }
'''
s=s.replace('\n    private fun parseTelemetry',insert+'\n    private fun parseTelemetry')
r.write_text(s)
m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'); s=m.read_text()
s=s.replace('import androidx.compose.ui.Modifier','import androidx.compose.ui.Modifier\nimport androidx.compose.ui.platform.LocalClipboardManager\nimport androidx.compose.ui.text.AnnotatedString')
s=s.replace('CONTROL CENTER • v0.5.3 RC • REGRESSION VALIDATED','GAMING TURBO • v0.6.1 RC • AI BRIDGE • REALTIME 1s')
old_chart='@Composable fun LineChartCard(title:String,values:List<Float>,min:Float,max:Float,current:String){Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold);Text(current,fontWeight=FontWeight.Bold)};Spacer(Modifier.height(10.dp));Canvas(Modifier.fillMaxWidth().height(120.dp)){if(values.size>1){val lo=min;val hi=max.coerceAtLeast(lo+1);val step=size.width/(values.size-1);fun y(v:Float)=size.height-(v.coerceIn(lo,hi)-lo)/(hi-lo)*size.height;for(i in 1 until values.size)drawLine(color=Green,start=Offset((i-1)*step,y(values[i-1])),end=Offset(i*step,y(values[i])),strokeWidth=3f)}}}}}'
new_chart='''@Composable fun LineChartCard(title:String,values:List<Float>,min:Float,max:Float,current:String){
    val clipboard=LocalClipboardManager.current
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString("["+title+"] "+current))}){Text("COPY")}}
        Text(current,fontWeight=FontWeight.Bold);Spacer(Modifier.height(10.dp))
        Canvas(Modifier.fillMaxWidth().height(120.dp)){if(values.size>1){val lo=min;val hi=max.coerceAtLeast(lo+1f);val step=size.width/(values.size-1);for(i in 1 until values.size){val y1=size.height-(values[i-1].coerceIn(lo,hi)-lo)/(hi-lo)*size.height;val y2=size.height-(values[i].coerceIn(lo,hi)-lo)/(hi-lo)*size.height;drawLine(color=Green,start=Offset((i-1)*step,y1),end=Offset(i*step,y2),strokeWidth=3f)}}}
    }}
}'''
if old_chart not in s: raise SystemExit('LineChartCard baseline not found')
s=s.replace(old_chart,new_chart)
old_ai='@Composable fun AI(s:RuntimeState){Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){BoxCard("AI SUMMARY",aiSummary(s));BoxCard("LOCAL BRAIN",s.brain.ifBlank{"No state published yet"});BoxCard("ADAPTIVE OPERATING ENVELOPE",s.envelope.ifBlank{"No envelope published yet"});BoxCard("GEMINI HTTP STATE",s.geminiHttp.ifBlank{"No Gemini HTTP state yet"},true);BoxCard("GEMINI SERVER STATE",s.geminiServer.ifBlank{"No server state / no active backoff"},true)}}'
new_ai='''@Composable fun AI(s:RuntimeState){
    val repo=remember{DjaegerRepository()}; var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}
    LaunchedEffect(request){val q=request;if(q!=null){val r=repo.setUserMode(q);result=r.second;request=null}}
    val supported=s.moduleVersion.contains("12.9.21") || s.moduleVersion.contains("12.9.22"); val retained=humanDecision(s); val brainText=if(s.brain.isBlank()) "No active Local Brain state.\\nLAST SESSION:\\n"+retained else s.brain
    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){
        BoxCard("GAMING TURBO MODE","Module: ${s.moduleVersion}\\nConfirmed active mode: ${s.userMode}\\nContract: ${if(supported) "DIRECT USER MODES READY" else "REQUIRES DJAEGER v12.9.21+"}\\n${if(result.isBlank()) "Select a mode below." else "Last command: $result"}",true)
        if(supported){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach{mode->Button(onClick={request=mode},enabled=request==null,contentPadding=PaddingValues(horizontal=7.dp,vertical=5.dp),modifier=Modifier.weight(1f)){Text(mode,style=MaterialTheme.typography.labelSmall)}}}}
        BoxCard("MODE AUTHORITY","The button sends only the official djaeger-ai mode command. DJAEGER controller confirms user_mode in runtime_status. Local Brain validates execution; Gemini receives USER_MODE as strategic context. Native thermal protection remains supreme.",true)
        BoxCard("AI SUMMARY LIVE",aiSummary(s));BoxCard("LOCAL BRAIN LIVE",brainText,true);BoxCard("ADAPTIVE OPERATING ENVELOPE LIVE",s.envelope.ifBlank{"No envelope published yet"},true);BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true);BoxCard("GEMINI HTTP STATE LIVE",s.geminiHttp.ifBlank{"No Gemini HTTP state yet"},true);BoxCard("GEMINI SERVER STATE LIVE",s.geminiServer.ifBlank{"No server state / no active backoff"},true)
    }
}'''
if old_ai not in s: raise SystemExit('AI baseline not found')
s=s.replace(old_ai,new_ai)
old_box='@Composable fun BoxCard(title:String,text:String,mono:Boolean=false){Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Text(title,color=Green,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.labelLarge);Spacer(Modifier.height(7.dp));Text(text,color=Color(0xFFE6EAF0),fontFamily=if(mono)FontFamily.Monospace else FontFamily.Default,style=MaterialTheme.typography.bodyMedium)}}}'
new_box='''@Composable fun BoxCard(title:String,text:String,mono:Boolean=false){val clipboard=LocalClipboardManager.current;Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(title,color=Green,fontWeight=FontWeight.Bold,style=MaterialTheme.typography.labelLarge);TextButton(onClick={clipboard.setText(AnnotatedString("DJAEGER v0.6.1 RC\\n["+title+"]\\n"+text))}){Text("COPY")}};Spacer(Modifier.height(7.dp));Text(text,color=Color(0xFFE6EAF0),fontFamily=if(mono)FontFamily.Monospace else FontFamily.Default,style=MaterialTheme.typography.bodyMedium)}}}'''
if old_box not in s: raise SystemExit('BoxCard baseline not found')
s=s.replace(old_box,new_box).replace('delay(2000)','delay(1000)').replace('delay(3000)','delay(1000)').replace('delay(5000)','delay(1000)')
m.write_text(s)
res=Path('app/src/main/res/drawable');res.mkdir(parents=True,exist_ok=True);(res/'ic_djaeger_gaming_turbo.xml').write_text('''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="#090B10" android:pathData="M12,8 L96,8 L104,20 L104,88 L92,100 L16,100 L4,88 L4,20 Z"/><path android:fillColor="#43E38A" android:pathData="M26,24 L62,24 C79,24 88,34 88,52 C88,70 78,82 59,82 L26,82 Z M40,37 L40,69 L58,69 C68,69 74,63 74,53 C74,43 68,37 58,37 Z"/><path android:fillColor="#FFC857" android:pathData="M59,14 L48,49 L61,49 L52,90 L81,43 L66,43 L78,14 Z"/></vector>''')
mf=Path('app/src/main/AndroidManifest.xml');ms=mf.read_text();
if 'android:icon=' not in ms:ms=ms.replace('<application','<application android:icon="@drawable/ic_djaeger_gaming_turbo"',1)
mf.write_text(ms)

from pathlib import Path
r=Path('app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'); s=r.read_text()
bridge='''
    private fun suStdin(command:String,input:String):Pair<Int,String>{
        return try{
            val p=ProcessBuilder("su","-c",command).redirectErrorStream(true).start()
            p.outputStream.bufferedWriter().use{w->w.write(input);w.newLine();w.flush()}
            val out=p.inputStream.bufferedReader().use{it.readText()}
            Pair(p.waitFor(),out)
        }catch(e:Exception){Pair(127,"BRIDGE_ERROR="+(e.message?:"unknown"))}
    }
    suspend fun geminiKeyStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-key-status"); Pair(rc==0,out.trim())
    }
    suspend fun saveGeminiKey(key:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(key.isBlank()) return@withContext Pair(false,"KEY_REJECTED=EMPTY")
        val (rc,out)=suStdin("djaeger-ai gemini-key-stdin",key); Pair(rc==0,out.trim())
    }
    suspend fun deleteGeminiKey():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-key-delete"); Pair(rc==0,out.trim())
    }
    suspend fun geminiChat(prompt:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        if(prompt.isBlank()) return@withContext Pair(false,"CHAT_ERROR=EMPTY_PROMPT")
        val (rc,out)=suStdin("djaeger-ai gemini-chat-stdin",prompt.take(1200)); Pair(rc==0,out.trim())
    }
'''
anchor='\n    private fun parseTelemetry'
if anchor not in s: raise SystemExit('repository insertion anchor not found')
s=s.replace(anchor,bridge+anchor,1); r.write_text(s)

m=Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'); s=m.read_text()
old='val repo=remember{DjaegerRepository()}; var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}'
new='''val repo=remember{DjaegerRepository()}; var request by remember{mutableStateOf<String?>(null)}; var result by remember{mutableStateOf("")}
    var bridgeOp by remember{mutableStateOf<String?>("STATUS")}; var bridgeStatus by remember{mutableStateOf("Checking Gemini key status...")}
    var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini about the current DJAEGER state.")}'''
if old not in s: raise SystemExit('AI state anchor not found')
s=s.replace(old,new,1)
old='LaunchedEffect(request){val q=request;if(q!=null){val r=repo.setUserMode(q);result=r.second;request=null}}'
new='''LaunchedEffect(request){val q=request;if(q!=null){val r=repo.setUserMode(q);result=r.second;request=null}}
    LaunchedEffect(bridgeOp){
        when(bridgeOp){
            "STATUS"->{val r=repo.geminiKeyStatus();bridgeStatus=r.second.ifBlank{"KEY_CONFIGURED=NO"}}
            "SAVE"->{val r=repo.saveGeminiKey(keyInput);bridgeStatus=r.second;if(r.first)keyInput=""}
            "DELETE"->{val r=repo.deleteGeminiKey();bridgeStatus=r.second}
            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}
        }
        bridgeOp=null
    }'''
if old not in s: raise SystemExit('AI effect anchor not found')
s=s.replace(old,new,1)
authority='BoxCard("MODE AUTHORITY","The button sends only the official djaeger-ai mode command. DJAEGER controller confirms user_mode in runtime_status. Local Brain validates execution; Gemini receives USER_MODE as strategic context. Native thermal protection remains supreme.",true)'
ui='''BoxCard("MODE AUTHORITY","The button sends only the official djaeger-ai mode command. DJAEGER controller confirms user_mode in runtime_status. Local Brain validates execution; Gemini receives USER_MODE as strategic context. Native thermal protection remains supreme.",true)
        BoxCard("GEMINI KEY STATUS",bridgeStatus,true)
        OutlinedTextField(value=keyInput,onValueChange={keyInput=it},label={Text("Gemini API key")},singleLine=true,visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="SAVE"},enabled=bridgeOp==null&&keyInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("SAVE / REPLACE")}
            Button(onClick={bridgeOp="STATUS"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("REFRESH")}
            Button(onClick={bridgeOp="DELETE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("DELETE")}
        }
        OutlinedTextField(value=chatInput,onValueChange={chatInput=it.take(1200)},label={Text("Ask DJAEGER Gemini")},minLines=2,maxLines=5,modifier=Modifier.fillMaxWidth(),enabled=bridgeOp==null)
        Button(onClick={bridgeOp="CHAT"},enabled=bridgeOp==null&&chatInput.isNotBlank(),modifier=Modifier.fillMaxWidth()){Text("ASK GEMINI")}
        BoxCard("GEMINI CHAT • ADVISORY ONLY",chatResult,true)'''
if authority not in s: raise SystemExit('mode authority anchor not found')
s=s.replace(authority,ui,1)
m.write_text(s)
