package com.djaeger.autocutmonitor;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

public class AutoCutReceiver extends BroadcastReceiver {
    public static final String ACTION = "com.djaeger.autocut.STATUS";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION.equals(intent.getAction())) return;

        SharedPreferences.Editor e =
                context.getSharedPreferences("autocut", Context.MODE_PRIVATE).edit();
        e.putString("mode", safe(intent.getStringExtra("mode")));
        e.putString("owner", safe(intent.getStringExtra("owner")));
        e.putInt("input_suspend", parseInt(intent.getStringExtra("input_suspend"), -1));
        e.putLong("module_ts", System.currentTimeMillis());
        e.apply();

        startMonitor(context);
    }

    static void startMonitor(Context context) {
        Intent svc = new Intent(context, MonitorService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(svc);
            } else {
                context.startService(svc);
            }
        } catch (RuntimeException ignored) {
        }
    }

    private static String safe(String s) { return s == null ? "" : s; }

    private static int parseInt(String s, int fallback) {
        if (s == null) return fallback;
        try { return Integer.parseInt(s.trim()); }
        catch (NumberFormatException e) { return fallback; }
    }
}
