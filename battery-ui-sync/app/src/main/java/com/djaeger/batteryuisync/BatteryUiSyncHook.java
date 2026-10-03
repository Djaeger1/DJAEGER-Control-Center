package com.djaeger.batteryuisync;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public final class BatteryUiSyncHook implements IXposedHookLoadPackage {
    private static final String TAG = "DJAEGER-BatteryUiSync";
    private static final String SYSTEM_UI = "com.android.systemui";

    @Override
    public void handleLoadPackage(final XC_LoadPackage.LoadPackageParam lpparam) {
        if (!SYSTEM_UI.equals(lpparam.packageName)) return;

        try {
            final Class<?> statusClass = XposedHelpers.findClass(
                    "com.android.keyguard.charge.MiuiBatteryStatus", lpparam.classLoader);

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

                                final Object status = param.args[0];
                                final Object view = XposedHelpers.getObjectField(param.thisObject, "this$0");
                                if (view == null) return;

                                final int incomingLevel = (Integer) XposedHelpers.callMethod(status, "getLevel");
                                final int cachedLevel = XposedHelpers.getIntField(view, "mLevel");

                                if (incomingLevel < 0 || incomingLevel > 100) return;

                                if (cachedLevel != incomingLevel) {
                                    // The MIUI callback received a new level but left the view cache stale.
                                    // Correct only the UI-side cache; BatteryService/sysfs are never touched.
                                    XposedHelpers.setIntField(view, "mLevel", incomingLevel);
                                    XposedHelpers.callMethod(view, "update");
                                    XposedBridge.log(TAG + ": corrected stale mLevel "
                                            + cachedLevel + " -> " + incomingLevel);
                                    return;
                                }

                                // MIUI can occasionally have the correct mLevel while the visible percent
                                // TextView remains stale. Re-apply only the percent text after the OEM callback.
                                // This is event-driven: no timer, polling, fake battery level, or SystemUI restart.
                                try {
                                    XposedHelpers.callMethod(view, "updatePercentText");
                                } catch (Throwable percentTextFailure) {
                                    // Conservative compatibility fallback for MIUI builds where the helper differs.
                                    XposedHelpers.callMethod(view, "update");
                                }
                            } catch (Throwable callbackFailure) {
                                // Never let a compatibility problem propagate into SystemUI.
                                XposedBridge.log(TAG + ": callback skipped safely: " + callbackFailure);
                            }
                        }
                    });

            XposedBridge.log(TAG + ": hook installed for " + lpparam.processName);
        } catch (Throwable installFailure) {
            // Fail closed: an unsupported SystemUI build remains completely OEM-controlled.
            XposedBridge.log(TAG + ": hook NOT installed: " + installFailure);
        }
    }
}
