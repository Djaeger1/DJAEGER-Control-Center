package com.djaeger.compat;

import android.app.Application;
import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

import top.canyie.pine.Pine;
import top.canyie.pine.PineConfig;
import top.canyie.pine.callback.MethodReplacement;

public final class HookEntry {
    private static final String TAG = "DJAEGER_R89_COMPAT";
    private static volatile boolean installed;

    private HookEntry() {}

    public static synchronized void install(Application app, ClassLoader appCl, final int pineFd) {
        if (installed) return;
        try {
            PineConfig.debug = false;
            PineConfig.debuggable = false;
            PineConfig.disableHiddenApiPolicy = false;
            PineConfig.disableHiddenApiPolicyForPlatformDomain = false;
            PineConfig.libLoader = new Pine.LibLoader() {
                @Override public void loadLib() {
                    System.load("/proc/self/fd/" + pineFd);
                }
            };
            Pine.ensureInitialized();

            final Class<?> main = Class.forName("com.djaeger.controlcenter.MainActivityKt", true, appCl);
            final Method status = findMethod(main, "StatusCard", 3);
            final Method box = findMethod(main, "BoxCard", 6);
            status.setAccessible(true);
            box.setAccessible(true);

            Pine.hook(status, new MethodReplacement() {
                @Override protected Object replaceCall(Pine.CallFrame frame) throws Throwable {
                    try {
                        Object s = frame.args[0];
                        Object composer = frame.args[1];
                        String body = buildBody(s);
                        box.invoke(null, "ENGINE / SESSION", body, false, composer, 0, 4);
                        return null;
                    } catch (Throwable t) {
                        Log.e(TAG, "render fallback", t);
                        return frame.invokeOriginalMethod();
                    }
                }
            });
            installed = true;
            writeStatus(app, "STATE=HOOKED\nCONTRACT=R89_CC112_CURRENT_APK\nAPK_REPLACED=NO\nLSPOSED_USED=NO\n");
            Log.i(TAG, "StatusCard compatibility hook installed");
        } catch (Throwable t) {
            writeStatus(app, "STATE=FAILED\nERROR=" + clean(t.toString()) + "\n");
            Log.e(TAG, "install failed", t);
        }
    }

    private static Method findMethod(Class<?> c, String name, int params) throws Exception {
        for (Method m : c.getDeclaredMethods()) {
            if (m.getName().equals(name) && m.getParameterTypes().length == params) return m;
        }
        throw new NoSuchMethodException(name + "/" + params);
    }

    private static String buildBody(Object s) throws Exception {
        long now = System.currentTimeMillis() / 1000L;
        long updated = asLong(call(s, "getUpdated"));
        boolean stale = updated <= 0 || now - updated > 15L;
        String active = str(call(s, "getActive"));
        String gameRaw = str(call(s, "getGame"));
        String windowRaw = str(call(s, "getWindow"));
        String workload = str(call(s, "getWorkloadContext"));
        String workloadClass = env(workload, "WORKLOAD_CLASS");
        if (workloadClass.isEmpty()) workloadClass = env(workload, "SUBJECT_CLASS");
        workloadClass = workloadClass.toUpperCase(Locale.US);
        String workloadPackage = env(workload, "PACKAGE");
        if (workloadPackage.isEmpty()) workloadPackage = "UNKNOWN";
        String workloadProfile = env(workload, "WORKLOAD_PROFILE");
        if (workloadProfile.isEmpty()) workloadProfile = "UNKNOWN";
        String visibleGame = env(workload, "VISIBLE_GAME");
        if (visibleGame.isEmpty() || visibleGame.equals("NONE") || visibleGame.equals("NA")) visibleGame = gameRaw;
        boolean gameVisible = !stale && !visibleGame.isEmpty() && !visibleGame.equals("NONE") && !visibleGame.equals("NA");
        boolean gameEngineActive = !stale && active.equals("1") && workloadClass.equals("GAME");

        String session;
        if (stale) session = "UNKNOWN / STALE";
        else if (gameEngineActive) session = "GAME ACTIVE";
        else if (workloadClass.equals("APP")) session = "APP ACTIVE • OBSERVE ONLY";
        else if (workloadClass.equals("SYSTEM")) session = "SYSTEM ACTIVE • OBSERVE ONLY";
        else session = "WAITING GAME";

        Object tel = call(s, "getTelemetry");
        long epoch = asLong(call(tel, "getEpoch"));
        boolean sampleFresh = Boolean.TRUE.equals(call(s, "getSampleFresh"));
        String sample = "—";
        if (epoch > 0) {
            String at = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date(epoch * 1000L));
            sample = at + (sampleFresh ? " • LIVE" : " • STALE");
        }

        String game = stale ? "—" : (gameEngineActive ? gameRaw : (gameVisible ? visibleGame : "NA"));
        String window = stale ? "—" : (gameEngineActive ? windowRaw : (gameVisible ? "MULTIWINDOW" : "INACTIVE"));
        String profile;
        if (stale) profile = "—";
        else if (gameEngineActive) profile = str(call(tel, "getProfile"));
        else if (workloadClass.equals("APP") || workloadClass.equals("SYSTEM")) profile = workloadProfile;
        else profile = "—";
        if (profile.isEmpty()) profile = "—";
        String execution = gameEngineActive ? "ACTIVE" : "BLOCKED / OBSERVE ONLY";
        String engine = stale ? "STALE" : "LIVE";
        String age = updated > 0 ? Math.max(0L, now - updated) + "s" : "—";
        String module = str(call(s, "getModuleVersion"));
        String controller = str(call(s, "getControllerPid"));
        String predictor = str(call(s, "getPredictorPid"));
        if (controller.isEmpty()) controller = "—";
        if (predictor.isEmpty()) predictor = "—";

        return "Engine: " + engine + " • age " + age
                + "\nSession: " + session
                + "\nModule: " + module
                + "\nGame: " + game
                + "\nWindow: " + window
                + "\nProfile: " + profile
                + "\nFocused workload: " + workloadClass + " • " + workloadPackage
                + "\nGame execution: " + execution
                + "\nLast device sample: " + sample
                + "\nController PID: " + controller + " • Predictor PID: " + predictor;
    }

    private static Object call(Object o, String name) throws Exception {
        Method m = o.getClass().getMethod(name);
        return m.invoke(o);
    }

    private static String env(String block, String key) {
        if (block == null) return "";
        String prefix = key + "=";
        for (String line : block.split("\\r?\\n")) {
            String x = line.trim();
            if (x.startsWith(prefix)) return strip(x.substring(prefix.length()).trim());
        }
        return "";
    }

    private static String strip(String s) {
        if (s.length() >= 2) {
            char a = s.charAt(0), b = s.charAt(s.length() - 1);
            if ((a == '\'' && b == '\'') || (a == '"' && b == '"')) return s.substring(1, s.length() - 1);
        }
        return s;
    }

    private static String str(Object o) { return o == null ? "" : String.valueOf(o); }
    private static long asLong(Object o) {
        if (o instanceof Number) return ((Number) o).longValue();
        try { return Long.parseLong(str(o)); } catch (Throwable ignored) { return 0L; }
    }

    private static void writeStatus(Application app, String body) {
        try {
            File f = new File(app.getFilesDir(), "djaeger_r89_compat.status");
            FileOutputStream out = new FileOutputStream(f, false);
            out.write((body + "UPDATED_AT=" + (System.currentTimeMillis()/1000L) + "\n").getBytes("UTF-8"));
            out.close();
        } catch (Throwable ignored) {}
    }

    private static String clean(String s) {
        return s == null ? "unknown" : s.replace('\n',' ').replace('\r',' ').replace('=','_');
    }
}
