package com.djaeger.chargecontrol;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public class MonitorService extends Service {
    public static final String CHANNEL_ID = "djaeger_charge_control";
    public static final int NOTIFICATION_ID = 8048;
    public static final String ACTION_BYPASS = "com.djaeger.chargecontrol.BYPASS";
    public static final String ACTION_AUTO = "com.djaeger.chargecontrol.AUTO";

    private static final long UPDATE_MS = 5000L;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean busy = new AtomicBoolean(false);

    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            refreshAsync();
            handler.postDelayed(this, UPDATE_MS);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(NOTIFICATION_ID, basicNotification("DJAEGER • membaca modul…",
                "Menyiapkan status baterai dan suhu"));
        handler.post(ticker);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        if (ACTION_BYPASS.equals(action) || ACTION_AUTO.equals(action)) {
            final boolean bypass = ACTION_BYPASS.equals(action);
            new Thread(() -> {
                if (bypass) ModuleBridge.bypass();
                else ModuleBridge.autoMode();
                refreshAsync();
            }, "djaeger-notif-control").start();
        } else {
            refreshAsync();
        }
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
                    CHANNEL_ID, "DJAEGER Charge Control", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("Mode bypass/AUTO, level baterai, dan suhu baterai");
            c.setShowBadge(false);
            getSystemService(NotificationManager.class).createNotificationChannel(c);
        }
    }

    private void refreshAsync() {
        if (!busy.compareAndSet(false, true)) return;
        new Thread(() -> {
            try {
                Snapshot s = readSnapshot();
                NotificationManager nm =
                        (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
                nm.notify(NOTIFICATION_ID, buildNotification(s));
            } finally {
                busy.set(false);
            }
        }, "djaeger-notify").start();
    }

    private Snapshot readSnapshot() {
        Intent batt = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int level = 0, scale = 100, tempDeciC = 0, plugged = 0;
        if (batt != null) {
            level = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, 0);
            scale = batt.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
            tempDeciC = batt.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0);
            plugged = batt.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
        }
        int soc = scale > 0 ? Math.round(level * 100f / scale) : level;
        float tempC = tempDeciC / 10f;

        ModuleBridge.State m = ModuleBridge.status();

        String title;
        String stateText;
        if (!m.rootOk) {
            title = "DJAEGER • ROOT REQUIRED";
            stateText = "Buka aplikasi dan izinkan root KernelSU";
        } else if (m.manualBypassActive()) {
            title = "DJAEGER • BYPASS AKTIF";
            stateText = "Input charging disuspend";
        } else if (m.bypassArmed()) {
            title = "DJAEGER • BYPASS SIAP";
            stateText = "Menunggu charger";
        } else if (m.autoCutActive()) {
            title = "DJAEGER • AUTO CUT";
            stateText = "Auto 99/90 • input suspend";
        } else {
            title = "DJAEGER • AUTO 99/90";
            stateText = plugged != 0 ? "Charging normal" : "Discharging";
        }

        String text = String.format(Locale.US, "%d%% • %.1f°C • %s", soc, tempC, stateText);
        return new Snapshot(title, text);
    }

    private Notification buildNotification(Snapshot s) {
        Intent launch = new Intent(this, MainActivity.class);
        PendingIntent openPi = PendingIntent.getActivity(
                this, 0, launch, pendingFlags());

        Intent bypass = new Intent(this, MonitorService.class).setAction(ACTION_BYPASS);
        PendingIntent bypassPi = PendingIntent.getService(
                this, 1, bypass, pendingFlags());

        Intent auto = new Intent(this, MonitorService.class).setAction(ACTION_AUTO);
        PendingIntent autoPi = PendingIntent.getService(
                this, 2, auto, pendingFlags());

        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        b.setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                .setContentTitle(s.title)
                .setContentText(s.text)
                .setSubText("POCO X5 5G")
                .setContentIntent(openPi)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setCategory(Notification.CATEGORY_STATUS)
                .addAction(new Notification.Action.Builder(
                        android.R.drawable.ic_lock_idle_charging, "BYPASS", bypassPi).build())
                .addAction(new Notification.Action.Builder(
                        android.R.drawable.ic_menu_revert, "AUTO", autoPi).build());

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            b.setPriority(Notification.PRIORITY_LOW);
        }
        return b.build();
    }

    private Notification basicNotification(String title, String text) {
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                .setContentTitle(title)
                .setContentText(text)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false);
        return b.build();
    }

    private int pendingFlags() {
        return Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                : PendingIntent.FLAG_UPDATE_CURRENT;
    }

    private static final class Snapshot {
        final String title;
        final String text;
        Snapshot(String title, String text) {
            this.title = title;
            this.text = text;
        }
    }
}
