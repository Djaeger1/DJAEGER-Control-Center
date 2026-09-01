package com.djaeger.batteryuisync;

import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public final class BatteryUiSyncHook implements IXposedHookLoadPackage {
    private static final String TAG = "DJAEGER-BatteryUiSync";
    private static final String SYSTEM_UI = "com.android.systemui";
    private static final Object LOCK = new Object();
    private static final List<WeakReference<Object>> VIEWS = new ArrayList<>();
    private static volatile int lastLevel = -1;
    private static volatile int lastLoggedLevel = -1;

    @Override
    public void handleLoadPackage(final XC_LoadPackage.LoadPackageParam lpparam) {
        if (!SYSTEM_UI.equals(lpparam.packageName)) return;
        try {
            final Class<?> viewClass = XposedHelpers.findClass("com.android.systemui.MiuiBatteryMeterView", lpparam.classLoader);
            final Class<?> statusClass = XposedHelpers.findClass("com.android.keyguard.charge.MiuiBatteryStatus", lpparam.classLoader);

            XposedBridge.hookAllConstructors(viewClass, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) { rememberView(param.thisObject); }
            });

            XposedHelpers.findAndHookMethod("com.android.systemui.MiuiBatteryMeterView$1", lpparam.classLoader,
                    "onRefreshBatteryInfo", statusClass, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    try {
                        if (param.args == null || param.args.length == 0 || param.args[0] == null) return;
                        final int level = (Integer) XposedHelpers.callMethod(param.args[0], "getLevel");
                        // MIUI emits transient level 0 while SystemUI is starting. Never propagate it.
                        if (level <= 0 || level > 100) return;
                        rememberView(XposedHelpers.getObjectField(param.thisObject, "this$0"));
                        lastLevel = level;
                        SyncStats stats = syncAll(level);
                        if (lastLoggedLevel != level || stats.directTextFixes > 0) {
                            lastLoggedLevel = level;
                            XposedBridge.log(TAG + ": v1.2 level=" + level
                                    + " live=" + stats.live
                                    + " attached=" + stats.attached
                                    + " shown=" + stats.shown
                                    + " views=" + stats.viewsUpdated
                                    + " textFix=" + stats.directTextFixes);
                        }
                    } catch (Throwable t) {
                        XposedBridge.log(TAG + ": callback skipped safely: " + t);
                    }
                }
            });

            XposedBridge.hookAllMethods(viewClass, "onAttachedToWindow", new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam param) {
                    rememberView(param.thisObject);
                    int level = lastLevel;
                    if (level > 0 && level <= 100) syncOne(param.thisObject, level, null);
                }
            });
            XposedBridge.log(TAG + ": v1.2 visible-text hook installed for " + lpparam.processName);
        } catch (Throwable t) {
            XposedBridge.log(TAG + ": hook NOT installed: " + t);
        }
    }

    private static void rememberView(Object view) {
        if (view == null) return;
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> it = VIEWS.iterator();
            while (it.hasNext()) {
                Object old = it.next().get();
                if (old == null) it.remove(); else if (old == view) return;
            }
            VIEWS.add(new WeakReference<>(view));
        }
    }

    private static SyncStats syncAll(int level) {
        SyncStats s = new SyncStats();
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> it = VIEWS.iterator();
            while (it.hasNext()) {
                Object obj = it.next().get();
                if (obj == null) { it.remove(); continue; }
                s.live++;
                if (obj instanceof View) {
                    View v = (View) obj;
                    if (v.isAttachedToWindow()) s.attached++;
                    if (v.isShown()) s.shown++;
                }
                syncOne(obj, level, s);
            }
        }
        return s;
    }

    private static void syncOne(Object obj, int level, SyncStats s) {
        try {
            int cached = XposedHelpers.getIntField(obj, "mLevel");
            if (cached != level) XposedHelpers.setIntField(obj, "mLevel", level);
            XposedHelpers.callMethod(obj, "update");
            if (s != null) s.viewsUpdated++;

            // Diagnostic + targeted repair: inspect TextViews under the OEM battery view.
            // Only replace a pure numeric percentage that is stale; labels/icons are untouched.
            if (obj instanceof View) {
                int fixes = syncNumericText((View) obj, level);
                if (s != null) s.directTextFixes += fixes;
            }
        } catch (Throwable ignored) {
            try { XposedHelpers.callMethod(obj, "updatePercentText"); } catch (Throwable ignored2) { }
        }
    }

    private static int syncNumericText(View root, int level) {
        int fixes = 0;
        if (root instanceof TextView) {
            TextView tv = (TextView) root;
            CharSequence cs = tv.getText();
            if (cs != null) {
                String text = cs.toString().trim();
                if (text.matches("\\d{1,3}")) {
                    try {
                        int old = Integer.parseInt(text);
                        if (old >= 0 && old <= 100 && old != level) {
                            tv.setText(String.valueOf(level));
                            fixes++;
                        }
                    } catch (NumberFormatException ignored) { }
                }
            }
        }
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) fixes += syncNumericText(group.getChildAt(i), level);
        }
        return fixes;
    }

    private static final class SyncStats {
        int live, attached, shown, viewsUpdated, directTextFixes;
    }
}
