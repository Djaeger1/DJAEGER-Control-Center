from pathlib import Path
import re

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
h = pkg / 'DjaegerHudService.kt'
s = h.read_text()

g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 30', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.11.4-rc-miui-freeform-phase4"', gs, count=1)
g.write_text(gs)

m = pkg / 'MainActivity.kt'
ms = m.read_text()
ms = ms.replace('GAMING TURBO • v0.11.3 RC • MIUI INTERACTION PHASE 3 • REALTIME 1s',
                'GAMING TURBO • v0.11.4 RC • MIUI FREEFORM PHASE 4 • REALTIME 1s')
ms = ms.replace('DJAEGER v0.11.3 RC', 'DJAEGER v0.11.4 RC')
m.write_text(ms)

old = r'''    /**
     * MIUI-native construction request:
     * 1) request freeform windowing mode 5 from ActivityManager,
     * 2) verify task/window state after launch,
     * 3) retry through cmd activity if the first launcher path was rejected.
     * Once the task is genuinely in MIUI freeform, MIUI owns drag, mini/pin,
     * restore, maximize and close transitions exactly like Game Turbo.
     */
    private fun launchMiuiFreeform(app: LaunchableApp) {
        val pkg = app.packageName.replace(Regex("[^A-Za-z0-9._]"), "")
        val activity = app.activityName.replace(Regex("[^A-Za-z0-9._$]"), "")
        if (pkg.isBlank() || activity.isBlank()) return
        toast("Membuka ${app.label} sebagai floating window…")
        thread(name = "djaeger-miui-freeform") {
            val component = "$pkg/$activity"
            val command =
                "am start --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1; " +
                "sleep 1; " +
                "STATE=\\\"${'$'}(dumpsys activity activities 2>/dev/null | grep -A 28 -B 4 '$pkg' | tail -n 80)\\\"; " +
                "printf '%s\\\\n' \\\"${'$'}STATE\\\"; " +
                "printf '%s\\\\n' \\\"${'$'}STATE\\\" | grep -Eqi 'windowingMode=5|mWindowingMode=5|freeform' && echo __DJAEGER_FREEFORM_CONFIRMED__ || echo __DJAEGER_FREEFORM_UNCONFIRMED__"
            var result = runRoot(command)
            if (!result.contains("__DJAEGER_FREEFORM_CONFIRMED__")) {
                result += runRoot(
                    "cmd activity start-activity --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1; " +
                        "sleep 1; dumpsys activity activities 2>/dev/null | grep -A 28 -B 4 '$pkg' | tail -n 80"
                )
            }
            val confirmed = Regex("windowingMode=5|mWindowingMode=5|freeform", RegexOption.IGNORE_CASE).containsMatchIn(result)
            mainHandler.post {
                toast(if (confirmed) "${app.label} • MIUI FREEFORM" else "${app.label} dibuka; MIUI tidak mengonfirmasi freeform")
                if (confirmed) { hudState = HudState.HANDLE; rebuildOverlayKeepingPosition() }
            }
        }
    }
'''

new = r'''    private enum class FreeformState { FREEFORM, MINI_FREEFORM, FULLSCREEN, FAILED, UNSUPPORTED }

    private data class FreeformCapability(
        val miuiFramework: Boolean,
        val miuiServiceHint: Boolean,
        val activityWindowingMode: Boolean
    )

    /**
     * Phase 4 freeform bridge.
     *
     * The SecurityCenter/Joyose reverse engineering established that MIUI Game
     * Turbo ultimately relies on MIUI freeform framework/services rather than
     * treating a successful `am start` return code as proof. DJAEGER therefore:
     *   1. discovers MIUI/freeform capability,
     *   2. requests the MIUI/ActivityTaskManager freeform mode exposed on device,
     *   3. reads the actual task/window state back,
     *   4. reports FULLSCREEN/FAILED/UNSUPPORTED instead of claiming success.
     *
     * We intentionally do not fabricate hidden Binder transaction numbers for
     * IMiuiFreeFormManager. Those must be learned from the exact ROM before a
     * direct Binder backend is enabled.
     */
    private fun discoverFreeformCapability(): FreeformCapability {
        val raw = runRoot(
            "FW=0; SVC=0; WM=0; " +
                "grep -Rqs 'MiuiFreeFormManager' /system/framework /system_ext/framework /product/framework 2>/dev/null && FW=1; " +
                "service list 2>/dev/null | grep -Eqi 'freeform|multiwindow|window' && SVC=1; " +
                "cmd activity help 2>/dev/null | grep -q -- '--windowingMode' && WM=1; " +
                "printf 'FW=%s\\nSVC=%s\\nWM=%s\\n' \\\"${'$'}FW\\\" \\\"${'$'}SVC\\\" \\\"${'$'}WM\\\""
        )
        fun yes(key: String) = Regex("(?m)^$key=1$").containsMatchIn(raw)
        return FreeformCapability(yes("FW"), yes("SVC"), yes("WM"))
    }

    private fun readFreeformState(pkg: String): FreeformState {
        val state = runRoot(
            "dumpsys activity activities 2>/dev/null | grep -A 36 -B 6 '$pkg' | tail -n 120; " +
                "dumpsys window windows 2>/dev/null | grep -A 24 -B 4 '$pkg' | tail -n 80"
        )
        val lower = state.lowercase(Locale.US)
        return when {
            lower.contains("mini freeform") || lower.contains("mini_freeform") ||
                lower.contains("small freeform") || lower.contains("small_freeform") -> FreeformState.MINI_FREEFORM
            Regex("windowingmode\\s*=\\s*5|mwindowingmode\\s*=\\s*5|windowingmode=freeform|\\bfreeform\\b", RegexOption.IGNORE_CASE)
                .containsMatchIn(state) -> FreeformState.FREEFORM
            Regex("windowingmode\\s*=\\s*1|mwindowingmode\\s*=\\s*1|fullscreen", RegexOption.IGNORE_CASE)
                .containsMatchIn(state) -> FreeformState.FULLSCREEN
            state.isBlank() -> FreeformState.FAILED
            else -> FreeformState.FAILED
        }
    }

    private fun launchMiuiFreeform(app: LaunchableApp) {
        val pkg = app.packageName.replace(Regex("[^A-Za-z0-9._]"), "")
        val activity = app.activityName.replace(Regex("[^A-Za-z0-9._$]"), "")
        if (pkg.isBlank() || activity.isBlank()) return
        toast("Membuka ${app.label} sebagai floating window…")
        thread(name = "djaeger-miui-freeform") {
            val cap = discoverFreeformCapability()
            if (!cap.activityWindowingMode && !cap.miuiFramework && !cap.miuiServiceHint) {
                mainHandler.post { toast("${app.label} • FREEFORM UNSUPPORTED") }
                return@thread
            }

            val component = "$pkg/$activity"
            // First request uses the framework-supported freeform mode. On MIUI,
            // WindowManager/ActivityTaskManager then hands ownership to MIUI's
            // freeform stack. A second command path is only a request fallback.
            runRoot("am start --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1")
            Thread.sleep(650)
            var state = readFreeformState(pkg)
            if (state != FreeformState.FREEFORM && state != FreeformState.MINI_FREEFORM && cap.activityWindowingMode) {
                runRoot("cmd activity start-activity --user 0 --windowingMode 5 -n '$component' >/dev/null 2>&1")
                Thread.sleep(650)
                state = readFreeformState(pkg)
            }

            mainHandler.post {
                val message = when (state) {
                    FreeformState.FREEFORM -> "${app.label} • MIUI FREEFORM"
                    FreeformState.MINI_FREEFORM -> "${app.label} • MIUI MINI FREEFORM"
                    FreeformState.FULLSCREEN -> "${app.label} • FULLSCREEN (freeform ditolak MIUI)"
                    FreeformState.UNSUPPORTED -> "${app.label} • FREEFORM UNSUPPORTED"
                    FreeformState.FAILED -> "${app.label} • FREEFORM FAILED"
                }
                toast(message)
                if (state == FreeformState.FREEFORM || state == FreeformState.MINI_FREEFORM) {
                    hudState = HudState.HANDLE
                    rebuildOverlayKeepingPosition()
                }
            }
        }
    }
'''

if old not in s:
    raise SystemExit('Build30: exact legacy launchMiuiFreeform block missing')
s = s.replace(old, new, 1)

required = [
    'private enum class FreeformState { FREEFORM, MINI_FREEFORM, FULLSCREEN, FAILED, UNSUPPORTED }',
    'discoverFreeformCapability()', 'readFreeformState(pkg: String)',
    'MiuiFreeFormManager', 'service list', '--windowingMode',
    'am start --user 0 --windowingMode 5',
    'cmd activity start-activity --user 0 --windowingMode 5',
    'dumpsys activity activities', 'dumpsys window windows',
    'FreeformState.FULLSCREEN', 'FreeformState.MINI_FREEFORM',
    'private fun updateOverlayContent()', 'dumpsys SurfaceFlinger --latency',
    '/data/adb/modules/djaeger_game_stabilizer/telemetry.csv',
    'listOf("AUTO", "DINGIN", "SEDANG", "HANGAT", "PANAS")',
    'djaeger-ai mode'
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'Build30 regression: required marker missing: {marker}')

# Never infer success from process return/output alone.
launch_body = s.split('private fun launchMiuiFreeform(app: LaunchableApp)',1)[1].split('private fun runDjaegerBoost()',1)[0]
if '__DJAEGER_FREEFORM_CONFIRMED__' in launch_body:
    raise SystemExit('Build30: legacy synthetic confirmation marker remains')
if 'readFreeformState(pkg)' not in launch_body:
    raise SystemExit('Build30: launch path lacks task/window readback')

apply_body = s.split('private fun applySessionState(active: Boolean)',1)[1].split('private fun isGameSessionActive',1)[0]
if 'updateOverlayContent()' not in apply_body or 'rebuildOverlayKeepingPosition()' in apply_body:
    raise SystemExit('Build30 regression: anti-flicker polling invariant broken')
for forbidden in ('settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft '):
    if forbidden in s:
        raise SystemExit(f'Build30 regression: forbidden unrelated mutation present: {forbidden}')

h.write_text(s)
print('Build 30 MIUI freeform phase 4 applied: capability discovery + strict task/window readback')
