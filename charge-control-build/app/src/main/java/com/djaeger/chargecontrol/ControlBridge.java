package com.djaeger.chargecontrol;

import android.content.Context;
import android.content.SharedPreferences;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

public final class ControlBridge {
    private static final String CONTROL_FILE = "djaeger_control.conf";

    private ControlBridge() {}

    public static boolean request(Context context, String mode) {
        if (!"AUTO".equals(mode) && !"BYPASS".equals(mode)) return false;

        File dir = context.getExternalFilesDir(null);
        if (dir == null) return false;
        if (!dir.exists() && !dir.mkdirs()) return false;

        File dst = new File(dir, CONTROL_FILE);
        File tmp = new File(dir, CONTROL_FILE + ".tmp");
        String body = "CONTROL_MODE=" + mode + "\nREQUEST_TS=" + System.currentTimeMillis() + "\n";

        try (FileOutputStream out = new FileOutputStream(tmp, false)) {
            out.write(body.getBytes(StandardCharsets.UTF_8));
            out.flush();
        } catch (IOException e) {
            return false;
        }

        if (dst.exists() && !dst.delete()) {
            tmp.delete();
            return false;
        }
        if (!tmp.renameTo(dst)) {
            tmp.delete();
            return false;
        }

        context.getSharedPreferences("autocut", Context.MODE_PRIVATE)
                .edit()
                .putString("requested_mode", mode)
                .putLong("request_ts", System.currentTimeMillis())
                .apply();
        return true;
    }

    public static State state(Context context) {
        SharedPreferences p = context.getSharedPreferences("autocut", Context.MODE_PRIVATE);
        return new State(
                p.getString("control_mode", "AUTO"),
                p.getString("runtime", "UNKNOWN"),
                p.getString("owner", "NONE"),
                p.getInt("input_suspend", -1),
                p.getInt("soc", -1),
                p.getInt("battery_temp", -1),
                p.getInt("skin_temp", -1),
                p.getInt("usb_online", -1),
                p.getLong("current_ua", 0L),
                p.getLong("module_ts", 0L)
        );
    }

    public static final class State {
        public final String control;
        public final String runtime;
        public final String owner;
        public final int suspend;
        public final int soc;
        public final int batteryTemp;
        public final int skinTemp;
        public final int usbOnline;
        public final long currentUa;
        public final long moduleTs;

        State(String control, String runtime, String owner, int suspend, int soc,
              int batteryTemp, int skinTemp, int usbOnline, long currentUa, long moduleTs) {
            this.control = control;
            this.runtime = runtime;
            this.owner = owner;
            this.suspend = suspend;
            this.soc = soc;
            this.batteryTemp = batteryTemp;
            this.skinTemp = skinTemp;
            this.usbOnline = usbOnline;
            this.currentUa = currentUa;
            this.moduleTs = moduleTs;
        }

        public boolean fresh() {
            return moduleTs > 0 && System.currentTimeMillis() - moduleTs <= 45000L;
        }

        public boolean bypassActive() {
            return fresh() && "BYPASS".equals(control)
                    && "MANUAL_BYPASS".equals(runtime)
                    && suspend == 1
                    && "MANUAL_BYPASS".equals(owner);
        }

        public boolean bypassArmed() {
            return fresh() && "BYPASS".equals(control)
                    && "BYPASS_ARMED".equals(runtime);
        }

        public boolean autoCutActive() {
            return fresh() && "AUTO".equals(control)
                    && "FULL_CUT".equals(runtime)
                    && suspend == 1
                    && "FULL_CUT".equals(owner);
        }
    }
}
