package com.djaeger.workdashboard;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
  private static final String DEFAULT_RUNTIME="http://192.168.42.129:8766";
  private static final String OLD_RUNTIME="http://192.168.42.129:8765";
  private WebView web;
  private SharedPreferences prefs;
  private String skinJs="";

  @Override protected void onCreate(Bundle b){
    super.onCreate(b);
    getWindow().setStatusBarColor(Color.rgb(2,8,18));
    getWindow().setNavigationBarColor(Color.rgb(2,8,18));
    prefs=getSharedPreferences("djaeger_work",MODE_PRIVATE);
    migrateRuntime();
    skinJs=readTextAsset("skin.js");

    web=new WebView(this);
    web.setBackgroundColor(Color.rgb(2,8,18));
    setContentView(web);

    WebSettings s=web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setAllowFileAccess(true);
    s.setAllowContentAccess(true);
    s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
    s.setCacheMode(WebSettings.LOAD_NO_CACHE);
    s.setTextZoom(100);

    web.addJavascriptInterface(new Bridge(),"DjaegerNative");
    web.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView view,String url){
        super.onPageFinished(view,url);
        if(url!=null && (url.startsWith("http://")||url.startsWith("https://")) && skinJs!=null && !skinJs.isEmpty()){
          view.evaluateJavascript(skinJs,null);
        }
      }
      @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error){
        super.onReceivedError(view,request,error);
        if(request!=null && request.isForMainFrame()) showOffline();
      }
    });

    openRuntime();
  }

  private void migrateRuntime(){
    String v=prefs.getString("runtime_url","");
    if(v==null || v.trim().isEmpty() || OLD_RUNTIME.equals(v.trim())){
      prefs.edit().putString("runtime_url",DEFAULT_RUNTIME).apply();
    }
  }

  private String base(){
    String v=prefs.getString("runtime_url",DEFAULT_RUNTIME);
    if(v==null)v=DEFAULT_RUNTIME;
    v=v.trim();
    while(v.endsWith("/"))v=v.substring(0,v.length()-1);
    if(OLD_RUNTIME.equals(v)){
      v=DEFAULT_RUNTIME;
      prefs.edit().putString("runtime_url",v).apply();
    }
    return (v.startsWith("http://")||v.startsWith("https://"))?v:DEFAULT_RUNTIME;
  }

  private void openRuntime(){ web.loadUrl(base()+"/"); }

  private String readTextAsset(String name){
    try(InputStream in=getAssets().open(name); ByteArrayOutputStream out=new ByteArrayOutputStream()){
      byte[] b=new byte[8192]; int n;
      while((n=in.read(b))>0)out.write(b,0,n);
      return out.toString(StandardCharsets.UTF_8.name());
    }catch(Exception e){return "";}
  }

  private String logoData(){
    try(InputStream in=getAssets().open("djaeger_logo.png"); ByteArrayOutputStream out=new ByteArrayOutputStream()){
      byte[] b=new byte[8192]; int n;
      while((n=in.read(b))>0)out.write(b,0,n);
      return "data:image/png;base64,"+Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP);
    }catch(Exception e){return "";}
  }

  private void showOffline(){
    final String html="<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><style>"
      +"body{margin:0;background:#020812;color:#f5f7fb;font-family:sans-serif;display:grid;place-items:center;min-height:100vh}"
      +".c{width:min(86vw,420px);background:#071a2d;border:1px solid #173a5d;border-radius:20px;padding:24px;text-align:center}"
      +"h2{margin:0 0 8px}p{color:#96a4b9;line-height:1.5}button{margin-top:14px;background:#2d79e8;color:white;border:0;border-radius:12px;padding:13px 20px;font-weight:800}</style></head>"
      +"<body><div class='c'><h2>DJAEGER WORK</h2><p>Runtime belum dapat dijangkau di <b>"+base()+"</b>.</p><button onclick='DjaegerNative.retry()'>REFRESH</button></div></body></html>";
    runOnUiThread(()->web.loadDataWithBaseURL(null,html,"text/html","UTF-8",null));
  }

  @Override public void onBackPressed(){
    if(web.canGoBack())web.goBack(); else super.onBackPressed();
  }

  @Override protected void onDestroy(){
    if(web!=null)web.destroy();
    super.onDestroy();
  }

  public class Bridge {
    @JavascriptInterface public String getRuntimeUrl(){return base();}
    @JavascriptInterface public boolean setRuntimeUrl(String u){
      if(u==null)return false;
      String v=u.trim();
      while(v.endsWith("/"))v=v.substring(0,v.length()-1);
      if(!(v.startsWith("http://")||v.startsWith("https://")))return false;
      prefs.edit().putString("runtime_url",v).apply();
      return true;
    }
    @JavascriptInterface public String getAdminToken(){return prefs.getString("admin_token","");}
    @JavascriptInterface public void setAdminToken(String t){prefs.edit().putString("admin_token",t==null?"":t).apply();}
    @JavascriptInterface public String getLastTab(){return prefs.getString("last_tab","work");}
    @JavascriptInterface public void setLastTab(String t){if(t!=null)prefs.edit().putString("last_tab",t).apply();}
    @JavascriptInterface public String logoData(){return MainActivity.this.logoData();}
    @JavascriptInterface public void retry(){runOnUiThread(()->openRuntime());}
    @JavascriptInterface public void copyText(String t){
      ClipboardManager cm=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);
      if(cm!=null)cm.setPrimaryClip(ClipData.newPlainText("DJAEGER WORK",t==null?"":t));
    }
    @JavascriptInterface public String appVersion(){return "1.4.0";}
  }
}
