package com.djaeger.chargecontrol;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * Compatibility receiver. Older DJAEGER module builds may still emit
 * com.djaeger.autocut.STATUS. The Charge Control app does not trust broadcast
 * data for control decisions; it re-reads the module through ModuleBridge.
 */
public class AutoCutReceiver extends BroadcastReceiver {
    public static final String ACTION = "com.djaeger.autocut.STATUS";

    @Override
    public void onReceive(Context context, Intent intent) {
        Intent svc = new Intent(context, MonitorService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(svc);
            } else {
                context.startService(svc);
            }
        } catch (RuntimeException ignored) {}
    }
}
