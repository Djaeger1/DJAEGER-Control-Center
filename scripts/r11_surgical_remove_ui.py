#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; a=root/'app/src/main/AndroidManifest.xml'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12114',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r11"',bs,count=1); b.write_text(bs)
ms=m.read_text(); ms=ms.replace('CONTROL CENTER • v0.12.1-r10.2 • LOCAL REALTIME 1s','CONTROL CENTER • v0.12.1-r11 • R78 SYNC • REALTIME 1s').replace('CONTROL CENTER • v0.12.1-r2 • DJAEGER-AI v12.9.50-r3 SYNC • REALTIME 1s','CONTROL CENTER • v0.12.1-r11 • R78 SYNC • REALTIME 1s'); m.write_text(ms)
# Only overlay permission is removed here. Core Control Center UI/features remain untouched.
manifest=a.read_text(); manifest=re.sub(r'\s*<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW"\s*/>','',manifest); a.write_text(manifest)
print('R11_BASELINE=R10.2_FULL_FEATURE')
print('R11_REMOVAL_SCOPE=HUD_LAUNCHER_MIUI_FREEFORM_ONLY')
