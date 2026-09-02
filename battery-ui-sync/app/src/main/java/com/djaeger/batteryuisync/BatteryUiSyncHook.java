package com.djaeger.batteryuisync;

import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
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
    private static final List<WeakReference<Object>> BATTERY_VIEWS = new ArrayList<>();
    private static final List<WeakReference<TextView>> TEXT_VIEWS = new ArrayList<>();
    private static volatile int lastLevel = -1;
    private static volatile int lastLoggedLevel = -1;

    @Override public void handleLoadPackage(final XC_LoadPackage.LoadPackageParam lpparam) {
        if (!SYSTEM_UI.equals(lpparam.packageName)) return;
        try {
            final Class<?> meterClass = XposedHelpers.findClass("com.android.systemui.MiuiBatteryMeterView", lpparam.classLoader);
            final Class<?> statusClass = XposedHelpers.findClass("com.android.keyguard.charge.MiuiBatteryStatus", lpparam.classLoader);

            XposedBridge.hookAllConstructors(meterClass, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam p) { rememberBatteryView(p.thisObject); }
            });

            // Observe TextViews created by SystemUI. Weak references only; no ownership/lifecycle changes.
            XposedBridge.hookAllConstructors(TextView.class, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam p) {
                    if (p.thisObject instanceof TextView) rememberTextView((TextView) p.thisObject);
                }
            });

            XposedHelpers.findAndHookMethod("com.android.systemui.MiuiBatteryMeterView$1", lpparam.classLoader,
                    "onRefreshBatteryInfo", statusClass, new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam p) {
                    try {
                        if (p.args == null || p.args.length == 0 || p.args[0] == null) return;
                        int level = (Integer) XposedHelpers.callMethod(p.args[0], "getLevel");
                        if (level <= 0 || level > 100) return;
                        rememberBatteryView(XposedHelpers.getObjectField(p.thisObject, "this$0"));
                        lastLevel = level;
                        Stats s = sync(level);
                        if (lastLoggedLevel != level || s.textFixed > 0) {
                            lastLoggedLevel = level;
                            XposedBridge.log(TAG + ": v1.3 level=" + level + " meters=" + s.meters
                                    + " meterShown=" + s.meterShown + " texts=" + s.texts
                                    + " candidates=" + s.candidates + " textFix=" + s.textFixed);
                        }
                    } catch (Throwable t) {
                        XposedBridge.log(TAG + ": callback skipped safely: " + t);
                    }
                }
            });

            XposedBridge.hookAllMethods(meterClass, "onAttachedToWindow", new XC_MethodHook() {
                @Override protected void afterHookedMethod(MethodHookParam p) {
                    rememberBatteryView(p.thisObject);
                    int level = lastLevel;
                    if (level > 0 && level <= 100) sync(level);
                }
            });
            XposedBridge.log(TAG + ": v1.3 global-text hook installed for " + lpparam.processName);
        } catch (Throwable t) {
            XposedBridge.log(TAG + ": hook NOT installed: " + t);
        }
    }

    private static Stats sync(int level) {
        Stats s = new Stats();
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> bi = BATTERY_VIEWS.iterator();
            while (bi.hasNext()) {
                Object o = bi.next().get();
                if (o == null) { bi.remove(); continue; }
                s.meters++;
                if (o instanceof View && ((View)o).isShown()) s.meterShown++;
                try {
                    if (XposedHelpers.getIntField(o, "mLevel") != level) XposedHelpers.setIntField(o, "mLevel", level);
                    XposedHelpers.callMethod(o, "update");
                } catch (Throwable ignored) { }
            }

            Iterator<WeakReference<TextView>> ti = TEXT_VIEWS.iterator();
            while (ti.hasNext()) {
                TextView tv = ti.next().get();
                if (tv == null) { ti.remove(); continue; }
                s.texts++;
                if (!isBatteryPercentCandidate(tv)) continue;
                s.candidates++;
                CharSequence cs = tv.getText();
                if (cs == null) continue;
                String raw = cs.toString().trim();
                String digits = raw.endsWith("%") ? raw.substring(0, raw.length() - 1).trim() : raw;
                try {
                    int old = Integer.parseInt(digits);
                    if (old >= 0 && old <= 100 && old != level) {
                        tv.setText(raw.endsWith("%") ? level + "%" : String.valueOf(level));
                        s.textFixed++;
                    }
                } catch (NumberFormatException ignored) { }
            }
        }
        return s;
    }

    private static boolean isBatteryPercentCandidate(TextView tv) {
        try {
            if (!tv.isAttachedToWindow() || !tv.isShown()) return false;
            CharSequence cs = tv.getText();
            if (TextUtils.isEmpty(cs)) return false;
            String raw = cs.toString().trim();
            String digits = raw.endsWith("%") ? raw.substring(0, raw.length() - 1).trim() : raw;
            if (!digits.matches("\\d{1,3}")) return false;
            int n = Integer.parseInt(digits);
            if (n < 0 || n > 100) return false;

            // Safety gate: only touch views whose resource/class ancestry identifies battery UI.
            View v = tv;
            for (int depth = 0; depth < 7 && v != null; depth++) {
                String idName = "";
                try { if (v.getId() != View.NO_ID) idName = v.getResources().getResourceEntryName(v.getId()); } catch (Throwable ignored) { }
                String cls = v.getClass().getName();
                String hay = (idName + " " + cls).toLowerCase();
                if (hay.contains("battery")) return true;
                ViewParent parent = v.getParent();
                v = parent instanceof View ? (View) parent : null;
            }
        } catch (Throwable ignored) { }
        return false;
    }

    private static void rememberBatteryView(Object o) {
        if (o == null) return;
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> it = BATTERY_VIEWS.iterator();
            while (it.hasNext()) { Object x = it.next().get(); if (x == null) it.remove(); else if (x == o) return; }
            BATTERY_VIEWS.add(new WeakReference<>(o));
        }
    }

    private static void rememberTextView(TextView tv) {
        synchronized (LOCK) {
            Iterator<WeakReference<TextView>> it = TEXT_VIEWS.iterator();
            while (it.hasNext()) { TextView x = it.next().get(); if (x == null) it.remove(); else if (x == tv) return; }
            TEXT_VIEWS.add(new WeakReference<>(tv));
        }
    }

    private static final class Stats { int meters, meterShown, texts, candidates, textFixed; }
}
