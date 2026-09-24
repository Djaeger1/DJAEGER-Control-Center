package com.djaeger.chargecontrol;

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

        SharedPreferences p = context.getSharedPreferences("autocut", Context.MODE_PRIVATE);
        SharedPreferences.Editor e = p.edit();

        String runtime = safe(intent.getStringExtra("mode"));
        String owner = safe(intent.getStringExtra("owner"));
        String control = safe(intent.getStringExtra("control_mode"));

        e.putString("runtime", runtime);
        e.putString("owner", owner);
        if (!control.isEmpty()) e.putString("control_mode", control);
        e.putInt("input_suspend", parseInt(intent.getStringExtra("input_suspend"), -1));
        e.putInt("soc", parseInt(intent.getStringExtra("soc"), -1));
        e.putInt("battery_temp", parseInt(intent.getStringExtra("battery_temp"), -1));
        e.putInt("skin_temp", parseInt(intent.getStringExtra("skin_temp"), -1));
        e.putInt("usb_online", parseInt(intent.getStringExtra("usb_online"), -1));
        e.putLong("current_ua", parseLong(intent.getStringExtra("current_ua"), 0L));
        e.putLong("module_ts", System.currentTimeMillis());

        String requested = p.getString("requested_mode", "");
        if (!control.isEmpty() && control.equals(requested)) {
            e.remove("requested_mode");
            e.remove("request_ts");
        }
        e.apply();

        Intent svc = new Intent(context, MonitorService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(svc);
            else context.startService(svc);
        } catch (RuntimeException ignored) {}
    }

    private static String safe(String s) {
        return s == null ? "" : s;
    }

    private static int parseInt(String s, int fallback) {
        try { return s == null ? fallback : Integer.parseInt(s.trim()); }
        catch (NumberFormatException e) { return fallback; }
    }

    private static long parseLong(String s, long fallback) {
        try { return s == null ? fallback : Long.parseLong(s.trim()); }
        catch (NumberFormatException e) { return fallback; }
    }
}
