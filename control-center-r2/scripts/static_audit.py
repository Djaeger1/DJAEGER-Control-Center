#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "src" / "main"
MAIN = (APP / "java/com/djaeger/controlcenter/MainActivity.kt").read_text()
REPO = (APP / "java/com/djaeger/controlcenter/DjaegerRepository.kt").read_text()
NORMALIZER = (APP / "java/com/djaeger/controlcenter/TelemetryNormalizer.kt").read_text()
MANIFEST = (APP / "AndroidManifest.xml").read_text()
GRADLE = (ROOT / "app/build.gradle.kts").read_text()
combined = MAIN + REPO + NORMALIZER + MANIFEST

failures = []

def require(condition: bool, label: str) -> None:
    if not condition:
        failures.append(label)
    else:
        print(f"PASS {label}")

require('versionName = "0.12.1-r2"' in GRADLE, "version-name-r2")
require('versionCode = 12102' in GRADLE, "version-code-r2")
require("v0.12.1-r2" in MAIN, "ui-version-r2")
require("v12.9.50-r3" in MAIN, "paired-module-r3")
require("gemini-3.6-flash" not in combined, "no-app-owned-model-override")

retired_tokens = (
    "GameTurboOverlayService",
    "DjaegerHudService",
    "BootReceiver",
    "START HUD",
    "STOP HUD",
    "canDrawOverlays",
    "TYPE_APPLICATION_OVERLAY",
)
for token in retired_tokens:
    require(token not in combined, f"retired-path-absent:{token}")

for permission in (
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.PACKAGE_USAGE_STATS",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.INTERNET",
    "android.permission.WRITE_SETTINGS",
    "android.permission.QUERY_ALL_PACKAGES",
):
    require(permission not in MANIFEST, f"permission-absent:{permission}")

require(MANIFEST.count("<activity") == 1, "single-activity-source-manifest")
require('android:name=".MainActivity"' in MANIFEST, "launcher-main-activity")
require('android:debuggable="true"' not in MANIFEST, "debuggable-not-enabled")
require('android:name="android.permission.DUMP"' in MANIFEST and 'tools:node="remove"' in MANIFEST, "dump-permission-removal")
require("androidx.startup.InitializationProvider" in MANIFEST and 'tools:node="remove"' in MANIFEST, "startup-provider-removal")
require("androidx.profileinstaller.ProfileInstallReceiver" in MANIFEST, "profile-receiver-removal")

write_patterns = (
    r">\s*/sys/",
    r"tee\s+/sys/",
    r"FileOutputStream\([^\n]*?/sys/",
    r"RandomAccessFile\([^\n]*?/sys/",
    r"writeText\([^\n]*?/sys/",
)
for pattern in write_patterns:
    require(re.search(pattern, combined) is None, f"sysfs-write-absent:{pattern}")

for pattern in (
    r"\biptables\b",
    r"\bip6tables\b",
    r"\bnft\b",
    r"\bsetprop\b",
    r"\bforce-stop\b",
    r"settings\s+put",
):
    require(re.search(pattern, combined) is None, f"unrelated-mutation-absent:{pattern}")

telemetry_lines = [line.strip() for line in REPO.splitlines() if line.strip().startswith("printf '") and "_" in line]
node_lines = [line for line in telemetry_lines if "cat /sys/" in line]
require(len(node_lines) == 8, "eight-live-node-reads")
for line in node_lines:
    require("printf '\\n'" in line, f"newline-safe:{line.split('=', 1)[0]}")

require("standardRaw" in NORMALIZER and "sm5602Raw" in NORMALIZER, "dual-current-input")
standard_position = NORMALIZER.find("currentCandidate(standardRaw")
fallback_position = NORMALIZER.find("currentCandidate(sm5602Raw")
require(standard_position >= 0 and fallback_position > standard_position, "standard-current-before-sm5602-fallback")
require('equals("Discharging", ignoreCase = true)' in NORMALIZER, "discharge-only-power-gate")
require("MIN_POWER_MW" in NORMALIZER and "MAX_POWER_MW" in NORMALIZER, "power-plausibility-gate")
require("MA_X1000" in NORMALIZER, "vendor-ma-normalization")
require("Float.NaN" in MAIN and "isFinite()" in MAIN, "chart-missing-value-gaps")
require("cpuT:Int=-1" in REPO and "littleKhz:Long=-1" in REPO, "missing-value-sentinels")
require("djaeger-ai gemini-chat-stdin" in REPO, "gemini-cli-bridge-retained")
require("djaeger-ai mode" in REPO, "typed-mode-bridge-retained")

if failures:
    print(f"STATIC_AUDIT=FAIL count={len(failures)}", file=sys.stderr)
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    raise SystemExit(1)

print("STATIC_AUDIT=PASS")
