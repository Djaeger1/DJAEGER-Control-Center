package com.djaeger.autocutmonitor;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import java.util.Locale;

public class MonitorService extends Service {
    public static final String CHANNEL_ID = "djaeger_autocut_monitor";
    public static final int NOTIFICATION_ID = 8048;
    private static final long UPDATE_MS = 5000L;
    private static final long BYPASS_FRESH_MS = 90000L;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            updateNotification();
            handler.postDelayed(this, UPDATE_MS);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        handler.removeCallbacks(ticker);
        handler.post(ticker);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        updateNotification();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacks(ticker);
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel c = new NotificationChannel(
                    CHANNEL_ID, "AutoCut battery monitor", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("Status charging, bypass AutoCut, daya baterai, dan suhu");
            c.setShowBadge(false);
            getSystemService(NotificationManager.class).createNotificationChannel(c);
        }
    }

    private Notification buildNotification() {
        Snapshot s = readSnapshot();

        Intent launch = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0, launch,
                Build.VERSION.SDK_INT >= 23
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT);

        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        b.setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                .setContentTitle(s.title)
                .setContentText(s.text)
                .setSubText("Redmi Note 8 Pro")
                .setContentIntent(pi)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setCategory(Notification.CATEGORY_STATUS);

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            b.setPriority(Notification.PRIORITY_LOW);
        }
        return b.build();
    }

    private void updateNotification() {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        nm.notify(NOTIFICATION_ID, buildNotification());
    }

    private Snapshot readSnapshot() {
        Intent batt = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        BatteryManager bm = (BatteryManager) getSystemService(BATTERY_SERVICE);

        int level = 0, scale = 100, tempDeciC = Integer.MIN_VALUE, voltageMv = 0;
        int status = BatteryManager.BATTERY_STATUS_UNKNOWN, plugged = 0;
        if (batt != null) {
            level = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, 0);
            scale = batt.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
            tempDeciC = batt.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Integer.MIN_VALUE);
            voltageMv = batt.getIntExtra(BatteryManager.EXTRA_VOLTAGE, 0);
            status = batt.getIntExtra(BatteryManager.EXTRA_STATUS, BatteryManager.BATTERY_STATUS_UNKNOWN);
            plugged = batt.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
        }
        int soc = scale > 0 ? Math.round(level * 100f / scale) : level;

        long currentUa = Long.MIN_VALUE;
        if (bm != null) currentUa = bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW);

        boolean currentValid = currentUa != Long.MIN_VALUE && Math.abs(currentUa) < 20000000L;
        boolean voltageValid = voltageMv > 2500 && voltageMv < 6000;
        boolean powerValid = currentValid && voltageValid;
        double powerW = powerValid
                ? (Math.abs((double) currentUa) * voltageMv) / 1_000_000_000.0
                : 0.0;

        SharedPreferences p = getSharedPreferences("autocut", MODE_PRIVATE);
        String mode = p.getString("mode", "UNKNOWN");
        String owner = p.getString("owner", "");
        int inputSuspend = p.getInt("input_suspend", -1);
        long moduleTs = p.getLong("module_ts", 0L);
        boolean moduleFresh = System.currentTimeMillis() - moduleTs <= BYPASS_FRESH_MS;
        boolean cutMode = "FULL_CUT".equals(mode) || "THERMAL_CUT".equals(mode);
        boolean bypass = moduleFresh && cutMode && inputSuspend == 1 && mode.equals(owner);

        boolean cablePresent = plugged != 0;
        boolean charging = !bypass && cablePresent &&
                (status == BatteryManager.BATTERY_STATUS_CHARGING || (currentValid && currentUa > 0));

        String temp = tempDeciC == Integer.MIN_VALUE
                ? null
                : String.format(Locale.US, "%.1f°C", tempDeciC / 10.0);

        String title;
        String metric = null;

        if (bypass) {
            title = "DJAEGER AutoCut • BYPASS";
            if (powerValid) metric = String.format(Locale.US, "Battery flow %.2f W", powerW);
        } else if (charging) {
            title = "DJAEGER AutoCut • CHARGING";
            if (powerValid) metric = String.format(Locale.US, "Masuk baterai %.2f W", powerW);
        } else if (!cablePresent) {
            title = "DJAEGER AutoCut • DISCHARGING";
            if (powerValid) metric = String.format(Locale.US, "Konsumsi baterai %.2f W", powerW);
        } else {
            title = "DJAEGER AutoCut • PLUGGED";
            if (powerValid) metric = String.format(Locale.US, "Battery flow %.2f W", powerW);
        }

        StringBuilder text = new StringBuilder();
        text.append(soc).append('%');
        if (temp != null) text.append(" • ").append(temp);
        if (metric != null) text.append(" • ").append(metric);

        return new Snapshot(title, text.toString());
    }

    private static class Snapshot {
        final String title;
        final String text;
        Snapshot(String title, String text) {
            this.title = title;
            this.text = text;
        }
    }
}
