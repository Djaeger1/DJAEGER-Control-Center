package com.djaeger.chargecontrol;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public final class ModuleBridge {
    private static final String HELPER =
            "/data/adb/modules/djaeger_autocut_charge/system/bin/djaeger-charge-control";

    private ModuleBridge() {}

    public static State status() { return run("status-line"); }
    public static State bypass() { return run("bypass"); }
    public static State autoMode() { return run("auto"); }

    private static State run(String command) {
        Process p = null;
        try {
            p = new ProcessBuilder("su", "-c", HELPER + " " + command)
                    .redirectErrorStream(true)
                    .start();

            boolean finished = p.waitFor(8, TimeUnit.SECONDS);
            if (!finished) {
                p.destroy();
                return State.error("ROOT_TIMEOUT");
            }

            StringBuilder out = new StringBuilder();
            try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line;
                while ((line = br.readLine()) != null) {
                    if (out.length() > 0) out.append(' ');
                    out.append(line.trim());
                }
            }

            String raw = out.toString().trim();
            if (p.exitValue() != 0 || !raw.contains("mode=")) {
                return State.error(raw.isEmpty() ? "ROOT_DENIED_OR_HELPER_MISSING" : raw);
            }
            return State.parse(raw);
        } catch (Exception e) {
            if (p != null) p.destroy();
            return State.error(e.getClass().getSimpleName());
        }
    }

    public static final class State {
        public final boolean rootOk;
        public final String mode;
        public final String runtimeState;
        public final String suspend;
        public final String owner;
        public final String enabled;
        public final String error;
        public final String raw;

        private State(boolean rootOk, String mode, String runtimeState, String suspend,
                      String owner, String enabled, String error, String raw) {
            this.rootOk = rootOk;
            this.mode = mode;
            this.runtimeState = runtimeState;
            this.suspend = suspend;
            this.owner = owner;
            this.enabled = enabled;
            this.error = error;
            this.raw = raw;
        }

        static State parse(String raw) {
            Map<String, String> m = new HashMap<>();
            for (String part : raw.split("\\s+")) {
                int i = part.indexOf('=');
                if (i > 0 && i < part.length() - 1) {
                    m.put(part.substring(0, i), part.substring(i + 1));
                }
            }
            return new State(
                    true,
                    m.getOrDefault("mode", "AUTO"),
                    m.getOrDefault("state", "UNKNOWN"),
                    m.getOrDefault("suspend", "NA"),
                    m.getOrDefault("owner", "NONE"),
                    m.getOrDefault("enabled", "1"),
                    "",
                    raw
            );
        }

        static State error(String error) {
            return new State(false, "UNKNOWN", "UNKNOWN", "NA", "NONE", "0",
                    error == null ? "UNKNOWN" : error, "");
        }

        public boolean manualBypassActive() {
            return rootOk && "BYPASS".equals(mode)
                    && "MANUAL_BYPASS".equals(runtimeState)
                    && "1".equals(suspend)
                    && "MANUAL_BYPASS".equals(owner);
        }

        public boolean autoCutActive() {
            return rootOk && "AUTO".equals(mode)
                    && "FULL_CUT".equals(runtimeState)
                    && "1".equals(suspend)
                    && "FULL_CUT".equals(owner);
        }

        public boolean bypassArmed() {
            return rootOk && "BYPASS".equals(mode) && "BYPASS_ARMED".equals(runtimeState);
        }
    }
}
