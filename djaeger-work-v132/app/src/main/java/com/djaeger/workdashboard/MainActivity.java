package com.djaeger.workdashboard;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.content.SharedPreferences;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.*;

public class MainActivity extends Activity {
  private static final String DEFAULT_RUNTIME="http://192.168.42.129:8765";
  private final ExecutorService io=Executors.newFixedThreadPool(4);
  private WebView web; private SharedPreferences prefs;
  @Override protected void onCreate(Bundle b){ super.onCreate(b); getWindow().setStatusBarColor(Color.rgb(3,8,18)); getWindow().setNavigationBarColor(Color.rgb(3,8,18)); prefs=getSharedPreferences("djaeger_work",MODE_PRIVATE); web=new WebView(this); web.setBackgroundColor(Color.rgb(3,8,18)); setContentView(web); WebSettings s=web.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true); s.setAllowContentAccess(true); s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW); s.setCacheMode(WebSettings.LOAD_NO_CACHE); s.setTextZoom(100); web.setWebViewClient(new WebViewClient()); web.addJavascriptInterface(new Bridge(),"DjaegerNative"); web.loadUrl("file:///android_asset/index.html"); }
  private String base(){ String v=prefs.getString("runtime_url",DEFAULT_RUNTIME); if(v==null)v=DEFAULT_RUNTIME; v=v.trim(); while(v.endsWith("/"))v=v.substring(0,v.length()-1); return (v.startsWith("http://")||v.startsWith("https://"))?v:DEFAULT_RUNTIME; }
  private void req(String method,String path,String body,String id){ io.execute(()->{ int code=0; String out="",err=""; HttpURLConnection c=null; try{ if(path==null||(!path.startsWith("/api/")&&!path.equals("/health")))throw new IllegalArgumentException("Unsupported path"); c=(HttpURLConnection)new URL(base()+path).openConnection(); c.setConnectTimeout(3500); c.setReadTimeout(9000); c.setUseCaches(false); c.setRequestProperty("Accept","application/json, text/plain, */*"); c.setRequestMethod(method==null?"GET":method.toUpperCase(Locale.US)); if("POST".equals(c.getRequestMethod())){ c.setDoOutput(true); c.setRequestProperty("Content-Type","application/json; charset=utf-8"); byte[] x=(body==null||body.isEmpty()?"{}":body).getBytes(StandardCharsets.UTF_8); try(OutputStream o=c.getOutputStream()){o.write(x);} } code=c.getResponseCode(); InputStream in=code>=400?c.getErrorStream():c.getInputStream(); if(in!=null){ try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){ StringBuilder sb=new StringBuilder(); String line; while((line=r.readLine())!=null)sb.append(line).append('\n'); out=sb.toString().trim(); } } }catch(Exception e){err=e.getClass().getSimpleName()+": "+(e.getMessage()==null?"request failed":e.getMessage());}finally{if(c!=null)c.disconnect();} final int fc=code; final String fo=out,fe=err; runOnUiThread(()->web.evaluateJavascript("window.__nativeResponse("+JSONObject.quote(id==null?"":id)+","+fc+","+JSONObject.quote(fo)+","+JSONObject.quote(fe)+")",null)); }); }
  @Override public void onBackPressed(){ web.evaluateJavascript("window.__djaegerBack?window.__djaegerBack():false",v->{if(!"true".equals(v))MainActivity.super.onBackPressed();}); }
  @Override protected void onDestroy(){ if(web!=null)web.destroy(); io.shutdownNow(); super.onDestroy(); }
  public class Bridge { @JavascriptInterface public void request(String m,String p,String b,String id){req(m,p,b,id);} @JavascriptInterface public String getRuntimeUrl(){return base();} @JavascriptInterface public boolean setRuntimeUrl(String u){ if(u==null)return false; String v=u.trim(); while(v.endsWith("/"))v=v.substring(0,v.length()-1); if(!(v.startsWith("http://")||v.startsWith("https://")))return false; prefs.edit().putString("runtime_url",v).apply(); return true;} @JavascriptInterface public String appVersion(){return "1.3.2";} }
}
