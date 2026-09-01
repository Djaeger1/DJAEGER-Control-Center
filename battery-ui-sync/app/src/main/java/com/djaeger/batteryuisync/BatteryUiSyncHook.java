package com.djaeger.batteryuisync;

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

    @Override
    public void handleLoadPackage(final XC_LoadPackage.LoadPackageParam lpparam) {
        if (!SYSTEM_UI.equals(lpparam.packageName)) return;

        try {
            final Class<?> viewClass = XposedHelpers.findClass(
                    "com.android.systemui.MiuiBatteryMeterView", lpparam.classLoader);
            final Class<?> statusClass = XposedHelpers.findClass(
                    "com.android.keyguard.charge.MiuiBatteryStatus", lpparam.classLoader);

            XposedBridge.hookAllConstructors(viewClass, new XC_MethodHook() {
                @Override
                protected void afterHookedMethod(MethodHookParam param) {
                    rememberView(param.thisObject);
                }
            });

            XposedHelpers.findAndHookMethod(
                    "com.android.systemui.MiuiBatteryMeterView$1",
                    lpparam.classLoader,
                    "onRefreshBatteryInfo",
                    statusClass,
                    new XC_MethodHook() {
                        @Override
                        protected void afterHookedMethod(MethodHookParam param) {
                            try {
                                if (param.args == null || param.args.length == 0 || param.args[0] == null) return;
                                final int incomingLevel = (Integer) XposedHelpers.callMethod(param.args[0], "getLevel");
                                if (incomingLevel < 0 || incomingLevel > 100) return;

                                final Object callbackView = XposedHelpers.getObjectField(param.thisObject, "this$0");
                                rememberView(callbackView);
                                lastLevel = incomingLevel;

                                int refreshed = refreshAllViews(incomingLevel);
                                if (refreshed > 0) {
                                    XposedBridge.log(TAG + ": resynced " + refreshed + " battery view(s) to " + incomingLevel);
                                }
                            } catch (Throwable callbackFailure) {
                                XposedBridge.log(TAG + ": callback skipped safely: " + callbackFailure);
                            }
                        }
                    });

            // When MIUI replaces/reattaches a status-bar view during lifecycle changes,
            // immediately seed that newly active view from the most recent real battery event.
            XposedBridge.hookAllMethods(viewClass, "onAttachedToWindow", new XC_MethodHook() {
                @Override
                protected void afterHookedMethod(MethodHookParam param) {
                    try {
                        rememberView(param.thisObject);
                        final int level = lastLevel;
                        if (level >= 0 && level <= 100) refreshView(param.thisObject, level);
                    } catch (Throwable ignored) {
                        // Fail closed: never disturb SystemUI lifecycle.
                    }
                }
            });

            XposedBridge.log(TAG + ": v1.1 active-view hook installed for " + lpparam.processName);
        } catch (Throwable installFailure) {
            XposedBridge.log(TAG + ": hook NOT installed: " + installFailure);
        }
    }

    private static void rememberView(Object view) {
        if (view == null) return;
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> it = VIEWS.iterator();
            while (it.hasNext()) {
                Object existing = it.next().get();
                if (existing == null) {
                    it.remove();
                } else if (existing == view) {
                    return;
                }
            }
            VIEWS.add(new WeakReference<>(view));
        }
    }

    private static int refreshAllViews(int level) {
        int count = 0;
        synchronized (LOCK) {
            Iterator<WeakReference<Object>> it = VIEWS.iterator();
            while (it.hasNext()) {
                Object view = it.next().get();
                if (view == null) {
                    it.remove();
                    continue;
                }
                if (refreshView(view, level)) count++;
            }
        }
        return count;
    }

    private static boolean refreshView(Object view, int level) {
        try {
            int cached = XposedHelpers.getIntField(view, "mLevel");
            if (cached != level) XposedHelpers.setIntField(view, "mLevel", level);

            // update() is the OEM method already proven to update icon, percent text,
            // charging presentation and invalidate the MiuiBatteryMeterView consistently.
            XposedHelpers.callMethod(view, "update");
            return true;
        } catch (Throwable failure) {
            try {
                XposedHelpers.setIntField(view, "mLevel", level);
                XposedHelpers.callMethod(view, "updatePercentText");
                return true;
            } catch (Throwable ignored) {
                return false;
            }
        }
    }
}
