from pathlib import Path
import re

g = Path("app/build.gradle.kts")
s = g.read_text()
s = s.replace("versionCode = 15", "versionCode = 16")
s = s.replace('versionName = "0.6.2-rc-ai-bridge-hardened-r2"', 'versionName = "0.7.0-rc-evolution-hud"')
g.write_text(s)

pkg = Path("app/src/main/java/com/djaeger/controlcenter")
pkg.mkdir(parents=True, exist_ok=True)

r = pkg / "DjaegerRepository.kt"
s = r.read_text()
s = s.replace('prompt.take(1200)', 'prompt.take(8000)')
anchor = "\n    private fun parseTelemetry"
extra = '''
    suspend fun geminiKnowledgeStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-knowledge-status"); Pair(rc==0,out.trim())
    }
    suspend fun geminiChatClear():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai gemini-chat-clear"); Pair(rc==0,out.trim())
    }
'''
if "geminiKnowledgeStatus()" not in s:
    if anchor not in s: raise SystemExit("repository parseTelemetry anchor not found")
    s = s.replace(anchor, extra + anchor, 1)
r.write_text(s)

m = pkg / "MainActivity.kt"
s = m.read_text()
s = s.replace("GAMING TURBO • v0.6.2 RC • AI BRIDGE HARDENED R2 • REALTIME 1s","GAMING TURBO • v0.7.0 RC • EVOLUTION HUD • REALTIME 1s")
s = s.replace("DJAEGER v0.6.2 RC", "DJAEGER v0.7.0 RC")
s = s.replace('val supported=s.moduleVersion.contains("12.9.21") || s.moduleVersion.contains("12.9.22");','val supported=s.moduleVersion.contains("12.9.");')
s = s.replace('onValueChange={chatInput=it.take(1200)}', 'onValueChange={chatInput=it.take(8000)}')

old_state = 'var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini about the current DJAEGER state.")}'
new_state = '''var keyInput by remember{mutableStateOf("")}; var chatInput by remember{mutableStateOf("")}; var chatResult by remember{mutableStateOf("Ask Gemini naturally. DJAEGER will provide relevant device context when available.")}
    var knowledgeStatus by remember{mutableStateOf("Knowledge status not loaded yet.")}'''
if old_state not in s: raise SystemExit("AI bridge state anchor not found")
s = s.replace(old_state, new_state, 1)

old_when = '''            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}
        }
        bridgeOp=null'''
new_when = '''            "CHAT"->{val r=repo.geminiChat(chatInput);chatResult=r.second.ifBlank{"CHAT_ERROR=EMPTY_RESPONSE"}}
            "KNOWLEDGE"->{val r=repo.geminiKnowledgeStatus();knowledgeStatus=r.second.ifBlank{"KNOWLEDGE_STATUS=EMPTY"}}
            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}
        }
        bridgeOp=null'''
if old_when not in s: raise SystemExit("Gemini operation switch anchor not found")
s = s.replace(old_when, new_when, 1)

old_authority = 'BoxCard("MODE AUTHORITY","The button sends only the official djaeger-ai mode command. DJAEGER controller confirms user_mode in runtime_status. Local Brain validates execution; Gemini receives USER_MODE as strategic context. Native thermal protection remains supreme.",true)'
new_authority = '''BoxCard("MODE AUTHORITY","Mode changes use only the trusted djaeger-ai mode interface. Native thermal protection remains independent and authoritative.",true)
        val ccContext=androidx.compose.ui.platform.LocalContext.current
        BoxCard("GAME LAUNCHER + FLOATING HUD","Launch games from DJAEGER and keep a draggable overlay above the game. HUD shows live FPS/temperature/mode and exposes only the trusted AUTO/DINGIN/SEDANG/HANGAT/PANAS controls.",true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={ccContext.startActivity(android.content.Intent(ccContext,GameLauncherActivity::class.java))},modifier=Modifier.weight(1f)){Text("GAME LAUNCHER")}
            Button(onClick={
                if(android.provider.Settings.canDrawOverlays(ccContext)){
                    val i=android.content.Intent(ccContext,DjaegerHudService::class.java)
                    if(android.os.Build.VERSION.SDK_INT>=26) ccContext.startForegroundService(i) else ccContext.startService(i)
                }else{
                    ccContext.startActivity(android.content.Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,android.net.Uri.parse("package:"+ccContext.packageName)))
                }
            },modifier=Modifier.weight(1f)){Text("START HUD")}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={ccContext.stopService(android.content.Intent(ccContext,DjaegerHudService::class.java))},modifier=Modifier.weight(1f)){Text("STOP HUD")}
            Button(onClick={bridgeOp="KNOWLEDGE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("EVOLUTION STATUS")}
        }
        BoxCard("GEMINI KNOWLEDGE + EVOLUTION",knowledgeStatus,true)'''
if old_authority not in s: raise SystemExit("mode authority card anchor not found")
s = s.replace(old_authority, new_authority, 1)

old_chat_button = 'Button(onClick={bridgeOp="CHAT"},enabled=bridgeOp==null&&chatInput.isNotBlank(),modifier=Modifier.fillMaxWidth()){Text("ASK GEMINI")}'
new_chat_button = '''Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            Button(onClick={bridgeOp="CHAT"},enabled=bridgeOp==null&&chatInput.isNotBlank(),modifier=Modifier.weight(1f)){Text("ASK GEMINI")}
            Button(onClick={bridgeOp="CLEAR_CHAT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NEW CHAT")}
        }'''
if old_chat_button not in s: raise SystemExit("chat button anchor not found")
s = s.replace(old_chat_button, new_chat_button, 1)
s = s.replace('BoxCard("GEMINI CHAT • ADVISORY ONLY",chatResult,true)', 'BoxCard("GEMINI CONVERSATION",chatResult,true)')
m.write_text(s)

(pkg / "GameLauncherActivity.kt").write_text(r'''package com.djaeger.controlcenter

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.net.Uri
import android.widget.*
import android.content.pm.ApplicationInfo

class GameLauncherActivity : Activity() {
    private val green = Color.rgb(67,227,138)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "DJAEGER Game Launcher"
        render()
    }
    private fun render() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28,28,28,28)
            setBackgroundColor(Color.rgb(9,11,16))
        }
        root.addView(TextView(this).apply {
            text = "DJAEGER GAME LAUNCHER"
            textSize = 22f
            setTextColor(green)
        })
        root.addView(TextView(this).apply {
            text = "Pilih game. DJAEGER HUD akan aktif sebelum game dibuka."
            setTextColor(Color.LTGRAY)
            setPadding(0,10,0,16)
        })
        root.addView(Button(this).apply {
            text = "START / AUTHORIZE FLOATING HUD"
            setOnClickListener { ensureHud() }
        })

        val scroll = ScrollView(this)
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val all = packageManager.queryIntentActivities(intent, 0)
            .filter { it.activityInfo.packageName != packageName }
            .sortedBy { it.loadLabel(packageManager).toString().lowercase() }
        val games = if (Build.VERSION.SDK_INT >= 26)
            all.filter { ri ->
                try { packageManager.getApplicationInfo(ri.activityInfo.packageName,0).category == ApplicationInfo.CATEGORY_GAME }
                catch (_:Exception) { false }
            } else emptyList()
        val chosen = if (games.isNotEmpty()) games else all
        if (chosen.isEmpty()) {
            list.addView(TextView(this).apply { text="Tidak ada aplikasi launcher yang terlihat."; setTextColor(Color.WHITE) })
        } else chosen.distinctBy { it.activityInfo.packageName }.forEach { ri ->
            val label = ri.loadLabel(packageManager).toString()
            list.addView(Button(this).apply {
                text = label
                isAllCaps = false
                setOnClickListener {
                    ensureHud()
                    packageManager.getLaunchIntentForPackage(ri.activityInfo.packageName)?.let { launch ->
                        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(launch)
                    }
                }
            })
        }
        scroll.addView(list)
        root.addView(scroll, LinearLayout.LayoutParams(-1,0,1f))
        setContentView(root)
    }
    private fun ensureHud() {
        if (!Settings.canDrawOverlays(this)) {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
            return
        }
        val i = Intent(this, DjaegerHudService::class.java)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
    }
}
''')

(pkg / "DjaegerHudService.kt").write_text(r'''package com.djaeger.controlcenter

import android.app.*
import android.content.*
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.*
import android.view.*
import android.widget.*
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.concurrent.thread

class DjaegerHudService : Service() {
    private lateinit var wm: WindowManager
    private var root: LinearLayout? = null
    private var status: TextView? = null
    private val handler = Handler(Looper.getMainLooper())
    private var expanded = true

    override fun onCreate() {
        super.onCreate()
        createChannel()
        val n = Notification.Builder(this, "djaeger_hud")
            .setContentTitle("DJAEGER Gaming HUD")
            .setContentText("Realtime overlay aktif")
            .setSmallIcon(R.drawable.ic_djaeger_gaming_turbo)
            .setOngoing(true)
            .build()
        startForeground(12927, n)
        showOverlay()
        handler.post(poll)
    }
    override fun onBind(intent: Intent?) = null
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        root?.let { try { wm.removeView(it) } catch (_:Exception) {} }
        root=null
        super.onDestroy()
    }
    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(NotificationChannel("djaeger_hud","DJAEGER Gaming HUD",NotificationManager.IMPORTANCE_LOW))
        }
    }
    private fun showOverlay() {
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(18,12,18,12)
            setBackgroundColor(Color.argb(225,9,11,16))
        }
        val header = LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        val st = TextView(this).apply { text="DJAEGER • LIVE"; setTextColor(Color.rgb(67,227,138)); textSize=14f }
        status=st
        header.addView(st, LinearLayout.LayoutParams(0,-2,1f))
        header.addView(Button(this).apply { text="—"; minWidth=0; setOnClickListener { toggleExpanded() } })
        header.addView(Button(this).apply { text="×"; minWidth=0; setOnClickListener { stopSelf() } })
        box.addView(header)

        val controls = LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL; tag="controls" }
        listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach { mode ->
            controls.addView(Button(this).apply {
                text=mode.take(3); textSize=9f; minWidth=0; setPadding(6,0,6,0)
                setOnClickListener { trustedMode(mode) }
            }, LinearLayout.LayoutParams(0,-2,1f))
        }
        box.addView(controls)

        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= 26) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply { gravity=Gravity.TOP or Gravity.START; x=20; y=150 }
        var sx=0f; var sy=0f; var ox=0; var oy=0
        st.setOnTouchListener { _,e ->
            when(e.action){
                MotionEvent.ACTION_DOWN->{sx=e.rawX;sy=e.rawY;ox=lp.x;oy=lp.y;true}
                MotionEvent.ACTION_MOVE->{lp.x=ox+(e.rawX-sx).toInt();lp.y=oy+(e.rawY-sy).toInt();try{wm.updateViewLayout(box,lp)}catch(_:Exception){};true}
                else->false
            }
        }
        root=box
        wm.addView(box,lp)
    }
    private fun toggleExpanded() {
        expanded=!expanded
        root?.findViewWithTag<View>("controls")?.visibility=if(expanded) View.VISIBLE else View.GONE
    }
    private fun trustedMode(mode:String) {
        thread { runRoot("djaeger-ai mode ${mode.lowercase()}") }
    }
    private val poll = object:Runnable {
        override fun run() {
            thread {
                val raw=runRoot("tail -n 1 /data/adb/djaeger_ai/telemetry.csv 2>/dev/null; echo __RT__; cat /data/adb/djaeger_ai/runtime_status 2>/dev/null")
                val text=format(raw)
                handler.post { status?.text=text }
            }
            handler.postDelayed(this,1000)
        }
    }
    private fun format(raw:String):String {
        val parts=raw.split("__RT__")
        val csv=parts.getOrNull(0)?.trim()?.lineSequence()?.lastOrNull().orEmpty().split(",")
        val rt=parts.getOrNull(1).orEmpty().lineSequence().mapNotNull {
            val p=it.indexOf('='); if(p>0) it.substring(0,p).trim().lowercase() to it.substring(p+1).trim() else null
        }.toMap()
        fun temp(i:Int):String {
            val v=csv.getOrNull(i)?.trim()?.toDoubleOrNull() ?: return "--"
            val c=if(v>1000) v/1000.0 else v
            return String.format("%.0f",c)
        }
        val fps=csv.getOrNull(9)?.trim()?.toDoubleOrNull()?.let{String.format("%.1f",it)} ?: "--"
        val mode=rt["user_mode"] ?: rt["mode"] ?: "AUTO"
        val game=rt["game"] ?: rt["game_id"] ?: "LIVE"
        return "DJAEGER • $fps FPS • ${temp(1)}°C/${temp(2)}°C • $mode • $game"
    }
    private fun runRoot(command:String):String = try {
        val p=ProcessBuilder("su","-c",command).redirectErrorStream(true).start()
        BufferedReader(InputStreamReader(p.inputStream)).use { it.readText() }.also { p.waitFor() }
    } catch (_:Exception) { "" }
}
''')

mf = Path("app/src/main/AndroidManifest.xml")
s = mf.read_text()
if 'android.permission.SYSTEM_ALERT_WINDOW' not in s:
    perms = '''    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
'''
    s = s.replace(">", ">\n" + perms, 1)

if "<queries>" not in s:
    queries = '''    <queries>
        <intent>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent>
    </queries>
'''
    s = s.replace("<application", queries + "    <application", 1)

components = '''        <activity
            android:name=".GameLauncherActivity"
            android:exported="false" />
        <service
            android:name=".DjaegerHudService"
            android:exported="false"
            android:foregroundServiceType="specialUse">
            <property
                android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
                android:value="Floating gaming telemetry HUD shown only when explicitly started by the user." />
        </service>
'''
if 'android:name=".GameLauncherActivity"' not in s:
    s = s.replace("</application>", components + "    </application>", 1)
mf.write_text(s)
