from pathlib import Path

# Build 14: targeted removal of AndroidX ProfileInstaller receiver from the app manifest.
# This receiver is the remaining source of android.permission.DUMP in the merged manifest.
# No DJAEGER control, telemetry, Gemini, mode, sysfs, or network behavior is changed.

mf = Path('app/src/main/AndroidManifest.xml')
s = mf.read_text()

if 'xmlns:tools=' not in s:
    s = s.replace('<manifest ', '<manifest xmlns:tools="http://schemas.android.com/tools" ', 1)

receiver = '''\n        <receiver\n            android:name="androidx.profileinstaller.ProfileInstallReceiver"\n            tools:node="remove" />\n'''

if 'androidx.profileinstaller.ProfileInstallReceiver' not in s:
    if '</application>' not in s:
        raise SystemExit('application closing tag not found')
    s = s.replace('</application>', receiver + '    </application>', 1)

mf.write_text(s)

# Keep the already-established version identity; this is a targeted hardening revision,
# not a functional feature release.
g = Path('app/build.gradle.kts')
gs = g.read_text()
gs = gs.replace('versionCode = 14', 'versionCode = 15')
gs = gs.replace('versionName = "0.6.2-rc-ai-bridge-hardened"', 'versionName = "0.6.2-rc-ai-bridge-hardened-r2"')
g.write_text(gs)

m = Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
ms = m.read_text().replace('GAMING TURBO • v0.6.2 RC • AI BRIDGE HARDENED • REALTIME 1s', 'GAMING TURBO • v0.6.2 RC • AI BRIDGE HARDENED R2 • REALTIME 1s')
m.write_text(ms)
