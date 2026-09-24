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

public class MonitorService extends Service {
    public static final String CHANNEL_ID = "djaeger_charge_control_v21";
    public static final int NOTIFICATION_ID = 8048;
    public static final String ACTION_BYPASS = "com.djaeger.chargecontrol.BYPASS";
    public static final String ACTION_AUTO = "com.djaeger.chargecontrol.AUTO";

    private static final long UPDATE_MS = 5000L;

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
        String action = intent == null ? null : intent.getAction();
        if (ACTION_BYPASS.equals(action)) {
            ControlBridge.request(this, "BYPASS");
        } else if (ACTION_AUTO.equals(action)) {
            ControlBridge.request(this, "AUTO");
        }
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
                    CHANNEL_ID, "DJAEGER Bypass & Temperature", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("Mode BYPASS/AUTO, level baterai, suhu battery dan suhu skin");
            c.setShowBadge(false);
            getSystemService(NotificationManager.class).createNotificationChannel(c);
        }
    }

    private void updateNotification() {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        nm.notify(NOTIFICATION_ID, buildNotification());
    }

    private Notification buildNotification() {
        Snapshot s = snapshot();

        Intent launch = new Intent(this, MainActivity.class);
        PendingIntent openPi = PendingIntent.getActivity(this, 0, launch, pendingFlags());

        Intent bypass = new Intent(this, MonitorService.class).setAction(ACTION_BYPASS);
        PendingIntent bypassPi = PendingIntent.getService(this, 1, bypass, pendingFlags());

        Intent auto = new Intent(this, MonitorService.class).setAction(ACTION_AUTO);
        PendingIntent autoPi = PendingIntent.getService(this, 2, auto, pendingFlags());

        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        b.setSmallIcon(android.R.drawable.ic_lock_idle_charging)
                .setContentTitle(s.title)
                .setContentText(s.text)
                .setStyle(new Notification.BigTextStyle().bigText(s.bigText))
                .setSubText("POCO X5 5G • AutoCut 99/90")
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

    private Snapshot snapshot() {
        ControlBridge.State s = ControlBridge.state(this);

        Intent batt = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int soc = s.soc;
        int battTempRaw = s.batteryTemp;
        if (batt != null) {
            int level = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, 0);
            int scale = batt.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
            soc = scale > 0 ? Math.round(level * 100f / scale) : level;
            battTempRaw = batt.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, battTempRaw);
        }

        String title;
        if (!s.fresh()) title = "DJAEGER • MENUNGGU MODUL";
        else if (s.bypassActive()) title = "DJAEGER • BYPASS AKTIF";
        else if (s.bypassArmed()) title = "DJAEGER • BYPASS SIAP";
        else if ("BYPASS".equals(s.control)) title = "DJAEGER • BYPASS REQUEST";
        else if (s.autoCutActive()) title = "DJAEGER • AUTO CUT";
        else title = "DJAEGER • AUTO 99/90";

        String battTemp = battTempRaw >= 0
                ? String.format(Locale.US, "%.1f°C", battTempRaw / 10.0)
                : "--";
        String skinTemp = s.skinTemp > 0
                ? String.format(Locale.US, "%.1f°C", s.skinTemp / 1000.0)
                : "--";

        String text = soc + "% • Batt " + battTemp + " • Skin " + skinTemp;
        String driver = s.suspend == 1 ? "CUT" : (s.suspend == 0 ? "NORMAL" : "--");
        String charger = s.usbOnline == 1 ? "Charger terhubung" :
                (s.usbOnline == 0 ? "Charger tidak terhubung" : "Charger --");
        String bigText = text
                + "\n" + charger + " • Driver " + driver
                + "\nControl " + s.control + " • Runtime " + s.runtime
                + "\nOwner " + s.owner + " • Current " + s.currentUa + " µA";

        return new Snapshot(title, text, bigText);
    }

    private int pendingFlags() {
        return Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                : PendingIntent.FLAG_UPDATE_CURRENT;
    }

    private static final class Snapshot {
        final String title;
        final String text;
        final String bigText;

        Snapshot(String title, String text, String bigText) {
            this.title = title;
            this.text = text;
            this.bigText = bigText;
        }
    }
}
