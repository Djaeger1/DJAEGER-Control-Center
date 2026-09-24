package com.djaeger.chargecontrol;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Locale;

public class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView batteryText;
    private TextView modeText;
    private TextView detailText;
    private Button bypassButton;
    private Button autoButton;

    private final Runnable refresher = new Runnable() {
        @Override public void run() {
            refreshAsync();
            handler.postDelayed(this, 3000L);
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

    private TextView text(float sp, boolean bold) {
        TextView v = new TextView(this);
        v.setTextSize(sp);
        if (bold) v.setTypeface(Typeface.DEFAULT_BOLD);
        return v;
    }

    private View spacer(int dp) {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Math.round(dp * getResources().getDisplayMetrics().density)));
        return v;
    }

    private void buildUi() {
        int pad = Math.round(22 * getResources().getDisplayMetrics().density);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setGravity(Gravity.TOP);

        TextView title = text(26f, true);
        title.setText("DJAEGER Charge Control");

        TextView sub = text(14f, false);
        sub.setText("POCO X5 5G • SM6375 • MIUI 14\nTerintegrasi dengan modul DJAEGER AutoCut");

        batteryText = text(22f, true);
        modeText = text(20f, true);
        detailText = text(14f, false);

        bypassButton = new Button(this);
        bypassButton.setText("AKTIFKAN BYPASS SEKARANG");
        bypassButton.setAllCaps(false);
        bypassButton.setOnClickListener(v -> applyMode(true));

        autoButton = new Button(this);
        autoButton.setText("KEMBALI KE AUTO 99/90");
        autoButton.setAllCaps(false);
        autoButton.setOnClickListener(v -> applyMode(false));

        TextView note = text(13f, false);
        note.setText(
                "Manual Bypass dapat diaktifkan pada level baterai berapa pun. " +
                "Saat kabel terpasang, modul menjaga Qualcomm input_suspend=1. " +
                "Jika kabel dilepas, mode tetap tersimpan sebagai BYPASS_ARMED dan akan aktif lagi saat kabel dipasang.\n\n" +
                "AUTO: cut 99% dan resume 90%.");

        root.addView(title);
        root.addView(sub);
        root.addView(spacer(26));
        root.addView(batteryText);
        root.addView(spacer(10));
        root.addView(modeText);
        root.addView(detailText);
        root.addView(spacer(22));
        root.addView(bypassButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(autoButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(spacer(18));
        root.addView(note);

        setContentView(root);
    }

    private void applyMode(boolean bypass) {
        bypassButton.setEnabled(false);
        autoButton.setEnabled(false);
        modeText.setText(bypass ? "Mengaktifkan BYPASS…" : "Mengembalikan AUTO…");

        new Thread(() -> {
            ModuleBridge.State s = bypass ? ModuleBridge.bypass() : ModuleBridge.autoMode();
            runOnUiThread(() -> {
                showState(s);
                bypassButton.setEnabled(true);
                autoButton.setEnabled(true);
                startMonitorService();
            });
        }, "djaeger-control").start();
    }

    private void refreshAsync() {
        final BatteryUi battery = readBattery();
        new Thread(() -> {
            ModuleBridge.State s = ModuleBridge.status();
            runOnUiThread(() -> {
                batteryText.setText(String.format(Locale.US, "%d%%  •  %.1f°C", battery.level, battery.tempC));
                showState(s);
            });
        }, "djaeger-refresh").start();
    }

    private void showState(ModuleBridge.State s) {
        if (!s.rootOk) {
            modeText.setText("ROOT BELUM DIIZINKAN");
            detailText.setText("Berikan akses root KernelSU untuk DJAEGER Charge Control.\n" + s.error);
            return;
        }

        if (s.manualBypassActive()) {
            modeText.setText("BYPASS AKTIF");
            detailText.setText("Input charging disuspend • node=1 • owner=MANUAL_BYPASS");
        } else if (s.bypassArmed()) {
            modeText.setText("BYPASS SIAP");
            detailText.setText("Charger tidak terpasang. Bypass akan aktif otomatis ketika charger tersambung.");
        } else if (s.autoCutActive()) {
            modeText.setText("AUTO • FULL CUT");
            detailText.setText("Auto 99/90 • input_suspend=1 • owner=FULL_CUT");
        } else {
            modeText.setText("AUTO 99/90");
            detailText.setText("State=" + s.runtimeState + " • input_suspend=" + s.suspend);
        }
    }

    private BatteryUi readBattery() {
        Intent batt = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (batt == null) return new BatteryUi(0, 0f);

        int level = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, 0);
        int scale = batt.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
        int t = batt.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0);
        int soc = scale > 0 ? Math.round(level * 100f / scale) : level;
        return new BatteryUi(soc, t / 10f);
    }

    private static final class BatteryUi {
        final int level;
        final float tempC;
        BatteryUi(int level, float tempC) {
            this.level = level;
            this.tempC = tempC;
        }
    }
}
