package com.djaeger.chargecontrol;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.Locale;

public class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());

    private TextView stateText;
    private TextView temperatureText;
    private TextView detailText;
    private Button bypassButton;
    private Button autoButton;

    private final Runnable refresher = new Runnable() {
        @Override public void run() {
            refreshUi();
            handler.postDelayed(this, 1000L);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestNotificationPermission();
        startMonitorService();
        buildUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.removeCallbacks(refresher);
        handler.post(refresher);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(refresher);
        super.onPause();
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 44);
        }
    }

    private void startMonitorService() {
        Intent svc = new Intent(this, MonitorService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(svc);
            else startService(svc);
        } catch (RuntimeException ignored) {}
    }

    private void buildUi() {
        int pad = dp(22);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(14, 17, 21));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, dp(28), pad, dp(28));

        TextView title = text("DJAEGER CHARGE CONTROL", 25f, true);
        title.setTextColor(Color.WHITE);

        TextView subtitle = text("POCO X5 5G • SM6375 • MIUI 14", 14f, false);
        subtitle.setTextColor(Color.rgb(150, 160, 170));
        subtitle.setPadding(0, dp(4), 0, dp(22));

        stateText = text("MENUNGGU MODUL", 23f, true);
        stateText.setGravity(Gravity.CENTER);
        stateText.setTextColor(Color.WHITE);
        stateText.setPadding(dp(12), dp(18), dp(12), dp(18));
        stateText.setBackgroundColor(Color.rgb(31, 37, 44));

        temperatureText = text("", 19f, true);
        temperatureText.setTextColor(Color.WHITE);
        temperatureText.setGravity(Gravity.CENTER);
        temperatureText.setPadding(0, dp(20), 0, dp(16));

        bypassButton = new Button(this);
        bypassButton.setText("Aktifkan Bypass");
        bypassButton.setAllCaps(false);
        bypassButton.setTextSize(17f);
        bypassButton.setOnClickListener(v -> request("BYPASS"));

        autoButton = new Button(this);
        autoButton.setText("Kembali ke Auto 99/90");
        autoButton.setAllCaps(false);
        autoButton.setTextSize(17f);
        autoButton.setOnClickListener(v -> request("AUTO"));

        detailText = text("", 15f, false);
        detailText.setTextColor(Color.rgb(195, 202, 209));
        detailText.setPadding(0, dp(20), 0, 0);

        TextView note = text(
                "BYPASS dapat diaktifkan pada level baterai berapa pun, misalnya 80% saat bermain game. " +
                "Aplikasi hanya mengirim perintah; modul DJAEGER tetap menjadi satu-satunya pengendali driver charging. " +
                "Saat BYPASS dimatikan, kontrol kembali ke AutoCut 99% → 90%.",
                13f, false);
        note.setTextColor(Color.rgb(130, 142, 153));
        note.setPadding(0, dp(24), 0, 0);

        root.addView(title, matchWrap());
        root.addView(subtitle, matchWrap());
        root.addView(stateText, matchWrap());
        root.addView(temperatureText, matchWrap());
        root.addView(bypassButton, matchWrap());
        root.addView(autoButton, matchWrap());
        root.addView(detailText, matchWrap());
        root.addView(note, matchWrap());

        scroll.addView(root);
        setContentView(scroll);
    }

    private void request(String mode) {
        boolean ok = ControlBridge.request(this, mode);
        if (!ok) {
            Toast.makeText(this, "Gagal mengirim perintah ke modul DJAEGER", Toast.LENGTH_LONG).show();
            return;
        }

        Toast.makeText(this,
                "BYPASS".equals(mode) ? "Mengaktifkan BYPASS…" : "Mengembalikan AUTO…",
                Toast.LENGTH_SHORT).show();
        refreshUi();
    }

    private void refreshUi() {
        ControlBridge.State s = ControlBridge.state(this);

        Intent batt = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int soc = s.soc;
        int batteryTemp = s.batteryTemp;
        if (batt != null) {
            int level = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, 0);
            int scale = batt.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
            soc = scale > 0 ? Math.round(level * 100f / scale) : level;
            batteryTemp = batt.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, batteryTemp);
        }

        if (!s.fresh()) {
            stateText.setText("MENUNGGU MODUL");
            stateText.setTextColor(Color.rgb(255, 193, 7));
        } else if (s.bypassActive()) {
            stateText.setText("BYPASS AKTIF");
            stateText.setTextColor(Color.rgb(76, 217, 100));
        } else if (s.bypassArmed()) {
            stateText.setText("BYPASS SIAP • PASANG CHARGER");
            stateText.setTextColor(Color.rgb(255, 193, 7));
        } else if ("BYPASS".equals(s.control)) {
            stateText.setText("MENGAKTIFKAN BYPASS…");
            stateText.setTextColor(Color.rgb(255, 193, 7));
        } else if (s.autoCutActive()) {
            stateText.setText("AUTO CUT AKTIF");
            stateText.setTextColor(Color.rgb(76, 217, 100));
        } else {
            stateText.setText("MODE AUTO");
            stateText.setTextColor(Color.WHITE);
        }

        String battTemp = batteryTemp >= 0
                ? String.format(Locale.US, "%.1f°C", batteryTemp / 10.0)
                : "--";
        String skinTemp = s.skinTemp > 0
                ? String.format(Locale.US, "%.1f°C", s.skinTemp / 1000.0)
                : "--";
        temperatureText.setText(soc + "%  •  Battery " + battTemp + "\nSkin " + skinTemp);

        bypassButton.setEnabled(!s.bypassActive());
        autoButton.setEnabled(!"AUTO".equals(s.control));

        String driver = s.suspend == 1 ? "CUT" : (s.suspend == 0 ? "NORMAL" : "--");
        String charger = s.usbOnline == 1 ? "Terhubung" :
                (s.usbOnline == 0 ? "Tidak terhubung" : "--");

        detailText.setText(
                "Control : " + s.control +
                "\nRuntime : " + s.runtime +
                "\nOwner : " + s.owner +
                "\nDriver : " + driver +
                "\nCharger : " + charger +
                "\nCurrent : " + s.currentUa + " µA" +
                "\nAutoCut : 99% → 90%");
    }

    private TextView text(String value, float sp, boolean bold) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(sp);
        if (bold) v.setTypeface(Typeface.DEFAULT_BOLD);
        return v;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
