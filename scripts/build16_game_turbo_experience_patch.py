from pathlib import Path

g=Path("app/build.gradle.kts")
s=g.read_text().replace("versionCode = 16","versionCode = 17").replace('versionName = "0.7.0-rc-evolution-hud"','versionName = "0.8.0-rc-game-turbo-experience"')
g.write_text(s)

pkg=Path("app/src/main/java/com/djaeger/controlcenter")

m=pkg/"MainActivity.kt"
s=m.read_text().replace("GAMING TURBO • v0.7.0 RC • EVOLUTION HUD • REALTIME 1s","GAMING TURBO • v0.8.0 RC • GAME TURBO EXPERIENCE • REALTIME 1s").replace("DJAEGER v0.7.0 RC","DJAEGER v0.8.0 RC")
s=s.replace('BoxCard("GAME LAUNCHER + FLOATING HUD","Launch games from DJAEGER and keep a draggable overlay above the game. HUD shows live FPS/temperature/mode and exposes only the trusted AUTO/DINGIN/SEDANG/HANGAT/PANAS controls.",true)','BoxCard("DJAEGER GAME TURBO","Buka game seperti biasa dari homescreen. DJAEGER membaca session modul dan otomatis memunculkan side handle/HUD ketika game aktif. Game Launcher tetap tersedia sebagai panel manual.",true)')
m.write_text(s)

(pkg/"GameLauncherActivity.kt").write_text(r'''package com.djaeger.controlcenter
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.net.Uri
import android.view.Gravity
import android.widget.*
import android.content.pm.ApplicationInfo

class GameLauncherActivity:Activity(){
    private val bg=Color.rgb(8,10,15);private val card=Color.rgb(18,23,32);private val green=Color.rgb(67,227,138);private val muted=Color.rgb(170,178,194)
    private fun dp(v:Int)=(v*resources.displayMetrics.density).toInt()
    private fun shape(c:Int,stroke:Int?=null,r:Int=18)=GradientDrawable().apply{setColor(c);cornerRadius=dp(r).toFloat();if(stroke!=null)setStroke(dp(1),stroke)}
    override fun onCreate(b:Bundle?){super.onCreate(b);render()}
    private fun render(){
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(18),dp(20),dp(18),dp(14));setBackgroundColor(bg)}
        root.addView(TextView(this).apply{text="DJAEGER";textSize=29f;setTextColor(green);typeface=android.graphics.Typeface.DEFAULT_BOLD})
        root.addView(TextView(this).apply{text="GAME TURBO  •  AUTO SESSION HUD";textSize=13f;setTextColor(muted);setPadding(0,dp(2),0,dp(18))})
        root.addView(TextView(this).apply{text="● AUTO GAME DETECTION";textSize=14f;gravity=Gravity.CENTER;setTextColor(green);setPadding(dp(16),dp(13),dp(16),dp(13));background=shape(card,green);setOnClickListener{startMonitor()}})
        root.addView(TextView(this).apply{text="GAME LIBRARY";textSize=13f;setTextColor(green);typeface=android.graphics.Typeface.DEFAULT_BOLD;setPadding(dp(2),dp(18),0,dp(10))})
        val sc=ScrollView(this);val list=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        val q=Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val all=packageManager.queryIntentActivities(q,0).filter{it.activityInfo.packageName!=packageName}
        val games=if(Build.VERSION.SDK_INT>=26)all.filter{try{packageManager.getApplicationInfo(it.activityInfo.packageName,0).category==ApplicationInfo.CATEGORY_GAME}catch(_:Exception){false}}else emptyList()
        (if(games.isNotEmpty())games else all).distinctBy{it.activityInfo.packageName}.sortedBy{it.loadLabel(packageManager).toString().lowercase()}.forEach{ri->
            val row=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL;setPadding(dp(12),dp(10),dp(10),dp(10));background=shape(card)}
            row.addView(ImageView(this).apply{setImageDrawable(ri.loadIcon(packageManager))},LinearLayout.LayoutParams(dp(44),dp(44)))
            val name=TextView(this).apply{text=ri.loadLabel(packageManager);textSize=16f;setTextColor(Color.WHITE);setPadding(dp(12),0,dp(8),0)}
            row.addView(name,LinearLayout.LayoutParams(0,-2,1f))
            row.addView(TextView(this).apply{text="PLAY";textSize=12f;gravity=Gravity.CENTER;setTextColor(bg);typeface=android.graphics.Typeface.DEFAULT_BOLD;background=shape(green);setPadding(dp(15),dp(9),dp(15),dp(9));setOnClickListener{startMonitor();packageManager.getLaunchIntentForPackage(ri.activityInfo.packageName)?.let{startActivity(it)}}})
            list.addView(row,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(10)})
        }
        sc.addView(list);root.addView(sc,LinearLayout.LayoutParams(-1,0,1f))
        setContentView(root)
    }
    private fun startMonitor(){
        if(!Settings.canDrawOverlays(this)){startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:$packageName")));return}
        val i=Intent(this,DjaegerHudService::class.java)
        if(Build.VERSION.SDK_INT>=26)startForegroundService(i)else startService(i)
    }
}
''')

(pkg/"DjaegerHudService.kt").write_text(r'''package com.djaeger.controlcenter
import android.app.*
import android.content.*
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.os.*
import android.provider.Settings
import android.view.*
import android.widget.*
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.concurrent.thread

class DjaegerHudService:Service(){
    private val h=Handler(Looper.getMainLooper());private lateinit var wm:WindowManager;private var v:View?=null;private var lp:WindowManager.LayoutParams?=null
    private var state=0;private var game=false;private var data=Data();private var scale=1f
    private val green=Color.rgb(67,227,138);private val bg=Color.argb(240,8,12,17);private val panel=Color.argb(247,13,18,25);private val muted=Color.rgb(175,184,199)
    data class Data(val fps:String="--",val frame:String="--",val cpu:String="--",val gpu:String="--",val mode:String="AUTO",val game:String="NA")
    private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
    private fun shape(fill:Int=panel,stroke:Int=green,r:Int=18)=GradientDrawable().apply{setColor(fill);cornerRadius=dp(r).toFloat();setStroke(dp(1),stroke)}
    override fun onCreate(){super.onCreate();wm=getSystemService(WINDOW_SERVICE)as WindowManager;if(Build.VERSION.SDK_INT>=26)getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("djaeger_turbo","DJAEGER Game Turbo",NotificationManager.IMPORTANCE_LOW));startForeground(12928,Notification.Builder(this,"djaeger_turbo").setContentTitle("DJAEGER Game Turbo").setContentText("Auto game detection aktif").setSmallIcon(R.drawable.ic_djaeger_gaming_turbo).setOngoing(true).build());h.post(poll)}
    override fun onStartCommand(i:Intent?,f:Int,id:Int)=START_STICKY
    override fun onBind(i:Intent?)=null
    override fun onDestroy(){h.removeCallbacksAndMessages(null);hide();super.onDestroy()}
    private val poll=object:Runnable{override fun run(){thread{val raw=root("cat /data/adb/djaeger_ai/runtime_status 2>/dev/null; echo __T__; tail -n 1 /data/adb/djaeger_ai/telemetry.csv 2>/dev/null");val d=parse(raw);val active=isActive(raw,d);h.post{data=d;if(active&&Settings.canDrawOverlays(this@DjaegerHudService)){if(!game){game=true;state=0;show()}else refresh()}else if(game){game=false;hide()}}};h.postDelayed(this,if(game)1000 else 1800)}}
    private fun isActive(raw:String,d:Data):Boolean{val u=raw.uppercase();return u.contains("WINDOW=ACTIVE")||u.contains("SESSION=ACTIVE")||u.contains("GAME_ACTIVE=1")||(d.game!="NA"&&d.game!="INACTIVE"&&!u.contains("WINDOW=INACTIVE"))}
    private fun parse(raw:String):Data{val r=raw.substringBefore("__T__").lineSequence().mapNotNull{val p=it.indexOf('=');if(p>0)it.substring(0,p).trim().lowercase() to it.substring(p+1).trim()else null}.toMap();val c=raw.substringAfter("__T__","").trim().split(",");fun n(i:Int)=c.getOrNull(i)?.trim()?.toDoubleOrNull();fun t(i:Int):String{val x=n(i)?:return"--";return String.format("%.0f",if(x>1000)x/1000 else x)};return Data(n(9)?.let{String.format("%.1f",it)}?:"--",(n(10)?:n(18))?.let{String.format("%.1f",it)}?:"--",t(1),t(2),r["user_mode"]?:r["mode"]?:"AUTO",r["game"]?:r["game_id"]?:r["package"]?:"NA")}
    private fun show(){hide();v=when(state){0->handle();1->compact();else->expanded()};val x=v?:return;lp=WindowManager.LayoutParams(WindowManager.LayoutParams.WRAP_CONTENT,WindowManager.LayoutParams.WRAP_CONTENT,if(Build.VERSION.SDK_INT>=26)WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,PixelFormat.TRANSLUCENT).apply{gravity=Gravity.TOP or Gravity.END;x=dp(8);y=dp(155)};drag(x);wm.addView(x,lp)}
    private fun hide(){v?.let{try{wm.removeView(it)}catch(_:Exception){}};v=null}
    private fun refresh(){val old=lp;val ox=old?.x?:dp(8);val oy=old?.y?:dp(155);show();lp?.let{it.x=ox;it.y=oy;try{wm.updateViewLayout(v,it)}catch(_:Exception){}}}
    private fun drag(x:View){var sx=0f;var sy=0f;var ox=0;var oy=0;x.setOnTouchListener{_,e->val p=lp?:return@setOnTouchListener false;when(e.action){MotionEvent.ACTION_DOWN->{sx=e.rawX;sy=e.rawY;ox=p.x;oy=p.y;false};MotionEvent.ACTION_MOVE->{p.x=(ox-(e.rawX-sx)).toInt().coerceAtLeast(0);p.y=(oy+(e.rawY-sy)).toInt().coerceAtLeast(0);try{wm.updateViewLayout(x,p)}catch(_:Exception){};true};else->false}}}
    private fun handle():View=TextView(this).apply{text="◆";textSize=18f;gravity=Gravity.CENTER;setTextColor(green);background=shape(bg,green,25);setPadding(dp(12),dp(9),dp(12),dp(9));setOnClickListener{state=1;show()}}
    private fun compact():View{val r=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL;background=shape(bg,green,25);setPadding(dp(12),dp(7),dp(8),dp(7))};fun tx(s:String,c:Int=Color.WHITE)=TextView(this).apply{text=s;textSize=12f;setTextColor(c);setPadding(dp(7),0,dp(7),0)};r.addView(tx("◆ DJAEGER",green));r.addView(tx("${data.fps} FPS"));r.addView(tx("${data.cpu}°C"));r.addView(tx(data.mode));r.addView(tx("⌄",green).apply{setOnClickListener{state=2;show()}});r.setOnLongClickListener{state=0;show();true};return r}
    private fun expanded():View{val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;background=shape(panel,green,18);setPadding(dp(13),dp(10),dp(13),dp(12))};val head=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL};head.addView(TextView(this).apply{text="◆  DJAEGER GAME TURBO";textSize=14f;setTextColor(green);typeface=Typeface.DEFAULT_BOLD},LinearLayout.LayoutParams(0,-2,1f));head.addView(action("−"){state=1;show()});head.addView(action("×"){game=false;hide()});root.addView(head);val met=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;background=shape(bg,Color.rgb(34,64,44),12);setPadding(dp(8),dp(10),dp(8),dp(10))};metric(met,"FPS",data.fps);metric(met,"FRAME","${data.frame} ms");metric(met,"CPU","${data.cpu}°C");metric(met,"GPU","${data.gpu}°C");root.addView(met,LinearLayout.LayoutParams(-1,-2).apply{topMargin=dp(9)});root.addView(TextView(this).apply{text="${data.game}  •  PLAYING";textSize=11f;setTextColor(muted);setPadding(dp(4),dp(9),0,dp(7))});val modes=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL};listOf("AUTO","DINGIN","SEDANG","HANGAT","PANAS").forEach{md->val c=when(md){"AUTO"->green;"DINGIN"->Color.rgb(60,150,255);"SEDANG"->Color.rgb(255,205,45);"HANGAT"->Color.rgb(255,145,35);else->Color.rgb(242,70,75)};modes.addView(TextView(this).apply{text=md;textSize=9f;gravity=Gravity.CENTER;setTextColor(c);background=shape(bg,c,9);setPadding(dp(6),dp(8),dp(6),dp(8));setOnClickListener{thread{root("djaeger-ai mode ${md.lowercase()}")}}},LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(2);marginEnd=dp(2)})};root.addView(modes);root.addView(TextView(this).apply{text="↔  RESIZE MANUAL";textSize=10f;gravity=Gravity.CENTER;setTextColor(muted);setPadding(dp(8),dp(10),dp(8),dp(5));setOnClickListener{scale=when{scale<.9f->1f;scale<1.1f->1.2f;else->.8f};v?.scaleX=scale;v?.scaleY=scale}});return root}
    private fun action(s:String,f:()->Unit)=TextView(this).apply{text=s;textSize=18f;gravity=Gravity.CENTER;setTextColor(Color.WHITE);setPadding(dp(10),dp(5),dp(10),dp(5));setOnClickListener{f()}}
    private fun metric(r:LinearLayout,l:String,value:String){val c=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER};c.addView(TextView(this).apply{text=l;textSize=9f;setTextColor(muted)});c.addView(TextView(this).apply{text=value;textSize=17f;setTextColor(green);typeface=Typeface.DEFAULT_BOLD});r.addView(c,LinearLayout.LayoutParams(0,-2,1f))}
    private fun root(cmd:String)=try{val p=ProcessBuilder("su","-c",cmd).redirectErrorStream(true).start();BufferedReader(InputStreamReader(p.inputStream)).use{it.readText()}.also{p.waitFor()}}catch(_:Exception){""}
}
''')

(pkg/"DjaegerBootReceiver.kt").write_text(r'''package com.djaeger.controlcenter
import android.content.*
import android.os.Build
class DjaegerBootReceiver:BroadcastReceiver(){
    override fun onReceive(c:Context,i:Intent){if(i.action==Intent.ACTION_BOOT_COMPLETED){val s=Intent(c,DjaegerHudService::class.java);try{if(Build.VERSION.SDK_INT>=26)c.startForegroundService(s)else c.startService(s)}catch(_:Exception){}}}
}
''')

mf=Path("app/src/main/AndroidManifest.xml")
s=mf.read_text()
if "android.permission.RECEIVE_BOOT_COMPLETED" not in s:s=s.replace('<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />','<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />\n    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />',1)
if 'android:name=".DjaegerBootReceiver"' not in s:
    s=s.replace("</application>",'''        <receiver android:name=".DjaegerBootReceiver" android:exported="true"><intent-filter><action android:name="android.intent.action.BOOT_COMPLETED" /></intent-filter></receiver>
    </application>''',1)
mf.write_text(s)
