package com.hermes.workdashboard;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String DEFAULT_DASH = "http://192.168.42.129:8766/";
    private static final String PREFS = "hermes_work_dashboard";
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private SharedPreferences prefs;
    private WebView web;
    private TextView status;
    private Button recover;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        buildUi();
        if (prefs.getString("token", "").trim().isEmpty()) showSettings(true);
        else load();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(11,15,20));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(10), dp(6), dp(6), dp(6));
        bar.setBackgroundColor(Color.rgb(20,26,34));

        TextView title = new TextView(this);
        title.setText("HERMES WORK");
        title.setTextColor(Color.WHITE);
        title.setTextSize(16);
        bar.addView(title, new LinearLayout.LayoutParams(0, -2, 1f));

        status = new TextView(this);
        status.setText("● CONNECTING");
        status.setTextColor(Color.LTGRAY);
        status.setPadding(dp(6),0,dp(6),0);
        bar.addView(status);

        Button refresh = new Button(this);
        refresh.setText("↻");
        refresh.setOnClickListener(v -> load());
        bar.addView(refresh, new LinearLayout.LayoutParams(dp(52), -2));

        Button settings = new Button(this);
        settings.setText("⚙");
        settings.setOnClickListener(v -> showSettings(false));
        bar.addView(settings, new LinearLayout.LayoutParams(dp(52), -2));
        root.addView(bar);

        recover = new Button(this);
        recover.setText("RUNTIME OFFLINE · TAP TO RECOVER");
        recover.setVisibility(View.GONE);
        recover.setOnClickListener(v -> recoverRuntime());
        root.addView(recover);

        web = new WebView(this);
        WebSettings ws = web.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                status.setText("● ONLINE");
                status.setTextColor(Color.rgb(79,209,123));
                recover.setVisibility(View.GONE);
                injectToken();
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                if (req.isForMainFrame()) {
                    status.setText("● OFFLINE");
                    status.setTextColor(Color.rgb(255,107,107));
                    recover.setVisibility(View.VISIBLE);
                }
            }
        });

        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1f));
        setContentView(root);
    }

    private String dashboardUrl() {
        String u = prefs.getString("url", DEFAULT_DASH).trim();
        if (u.isEmpty()) u = DEFAULT_DASH;
        if (!u.startsWith("http://") && !u.startsWith("https://")) u = "http://" + u;
        if (!u.endsWith("/")) u += "/";
        return u;
    }

    private String token() { return prefs.getString("token", "").trim(); }

    private void load() {
        status.setText("● CONNECTING");
        status.setTextColor(Color.LTGRAY);
        web.loadUrl(dashboardUrl());
    }

    private void injectToken() {
        String t = JSONObject.quote(token());
        web.evaluateJavascript("(function(){var e=document.getElementById('token');if(e){e.value="+t+";}})();", null);
    }

    private String bootstrapUrl() throws Exception {
        URL u = new URL(dashboardUrl());
        return u.getProtocol() + "://" + u.getHost() + ":8765";
    }

    private void recoverRuntime() {
        recover.setEnabled(false);
        status.setText("● RECOVERING");
        status.setTextColor(Color.YELLOW);
        io.execute(() -> {
            try {
                String cmd = "ROOT=/data/adb/hermes_work; VER=$(cat $ROOT/current_release 2>/dev/null); REL=$ROOT/releases/$VER; [ -x \"$REL/bin/workd\" ] || exit 7; PID=$ROOT/state/workd.pid; OLD=$(cat $PID 2>/dev/null); [ -n \"$OLD\" ] && kill \"$OLD\" 2>/dev/null; nohup \"$REL/bin/workd\" --root \"$ROOT\" --release \"$REL\" >>\"$ROOT/logs/workd.log\" 2>&1 & echo $! > \"$PID\"; sleep 2";
                JSONObject body = new JSONObject();
                body.put("command", cmd);
                HttpResult r = request(bootstrapUrl()+"/api/exec","POST",body.toString(),true);
                if (r.code < 200 || r.code >= 300) throw new Exception("HTTP "+r.code+" "+r.body);
                runOnUiThread(() -> {
                    recover.setEnabled(true);
                    load();
                });
            } catch(Exception e) {
                runOnUiThread(() -> {
                    status.setText("● RECOVERY FAILED");
                    status.setTextColor(Color.rgb(255,107,107));
                    recover.setEnabled(true);
                    new AlertDialog.Builder(this).setTitle("Recovery gagal").setMessage(e.getMessage()).setPositiveButton("OK",null).show();
                });
            }
        });
    }

    private HttpResult request(String target, String method, String body, boolean auth) throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(target).openConnection();
        c.setRequestMethod(method); c.setConnectTimeout(5000); c.setReadTimeout(20000); c.setUseCaches(false);
        c.setRequestProperty("Accept","application/json, text/plain, */*");
        if(auth)c.setRequestProperty("X-Hermes-Token",token());
        if(body!=null){
            byte[] data=body.getBytes(StandardCharsets.UTF_8);
            c.setDoOutput(true); c.setRequestProperty("Content-Type","application/json; charset=utf-8");
            c.setFixedLengthStreamingMode(data.length);
            try(OutputStream os=c.getOutputStream()){os.write(data);}
        }
        int code=c.getResponseCode();
        InputStream in=code>=400?c.getErrorStream():c.getInputStream();
        StringBuilder sb=new StringBuilder();
        if(in!=null)try(BufferedReader br=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){
            String line; while((line=br.readLine())!=null)sb.append(line).append('\n');
        }
        c.disconnect(); return new HttpResult(code,sb.toString());
    }

    private void showSettings(boolean first) {
        LinearLayout box=new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(dp(16),dp(4),dp(16),0);
        EditText u=new EditText(this); u.setHint("Dashboard URL"); u.setSingleLine(true); u.setText(prefs.getString("url",DEFAULT_DASH)); box.addView(u);
        EditText t=new EditText(this); t.setHint("ADMIN TOKEN"); t.setSingleLine(true); t.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD); t.setText(token()); box.addView(t);

        AlertDialog d=new AlertDialog.Builder(this).setTitle("HERMES WORK Connection").setView(box)
                .setPositiveButton("SAVE",null).setNegativeButton(first?"LATER":"CANCEL",null).create();
        d.setOnShowListener(x->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            String us=u.getText().toString().trim(); if(us.isEmpty())us=DEFAULT_DASH;
            prefs.edit().putString("url",us).putString("token",t.getText().toString().trim()).apply();
            d.dismiss(); load();
        }));
        d.show();
    }

    private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}

    @Override public void onBackPressed() {
        if(web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    @Override protected void onDestroy(){io.shutdownNow();web.destroy();super.onDestroy();}

    static class HttpResult{final int code;final String body;HttpResult(int c,String b){code=c;body=b==null?"":b;}}
}
