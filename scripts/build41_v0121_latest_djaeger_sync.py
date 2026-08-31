from pathlib import Path
import re
import xml.etree.ElementTree as ET

pkg = Path('app/src/main/java/com/djaeger/controlcenter')
main = pkg / 'MainActivity.kt'
repo = pkg / 'DjaegerRepository.kt'
gradle = Path('app/build.gradle.kts')
manifest = Path('app/src/main/AndroidManifest.xml')

# Keep the v0.12.1 visual/code baseline; only remove the four retired gaming UI features
# and align AI compatibility/status text with DJAEGER-AI v12.9.50-r1.
gs = gradle.read_text()
gs = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 41', gs, count=1)
gs = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.12.1-djaeger-ai-12.9.50-r1-sync"', gs, count=1)
gradle.write_text(gs)

s = main.read_text()
s = s.replace('GAMING TURBO • v0.12.1 RC • HARDWARE OVERLAY FIX • REALTIME 1s',
              'CONTROL CENTER • v0.12.1 • DJAEGER-AI v12.9.50-r1 SYNC • REALTIME 1s')
s = s.replace('DJAEGER v0.12.1 RC', 'DJAEGER v0.12.1 • AI SYNC')

# Current stable/protected module baseline. A contains check also accepts suffix/build labels.
s = re.sub(
    r'val supported\s*=\s*[^;\n]+;',
    'val supported=s.moduleVersion.contains("12.9.50");',
    s,
    count=1
)

# Remove the exact feature family requested by owner: Game Launcher, Start HUD,
# Stop HUD, Evolution Status. Keep compact UI, tabs, logs, COPY, key manager and chat.
start = s.find('        val ccContext=androidx.compose.ui.platform.LocalContext.current')
end_marker = '        BoxCard("GEMINI KNOWLEDGE + EVOLUTION",knowledgeStatus,true)'
if start >= 0:
    end = s.find(end_marker, start)
    if end < 0:
        raise SystemExit('Build41: retired feature block end marker missing')
    end += len(end_marker)
    replacement = '''        BoxCard("DJAEGER-AI SYNC","Target module: v12.9.50-r1\\nTransport: Gemini v12.9.50 protected baseline\\nControl path: official typed djaeger-ai commands only\\nDisplay/battery cooling: not controlled by Control Center",true)'''
    s = s[:start] + replacement + s[end:]
else:
    # Fail closed if labels still exist but the expected block cannot be found.
    if any(x in s for x in ('GAME LAUNCHER','START HUD','STOP HUD','EVOLUTION STATUS')):
        raise SystemExit('Build41: retired feature labels found outside expected block')

# Old Evolution-only status state/operation is no longer surfaced.
s = re.sub(r'\s*var knowledgeStatus by remember\{mutableStateOf\("Knowledge status not loaded yet\."\)\}', '', s, count=1)
s = re.sub(r'\n\s*"KNOWLEDGE"->\{val r=repo\.geminiKnowledgeStatus\(\);knowledgeStatus=r\.second\.ifBlank\{"KNOWLEDGE_STATUS=EMPTY"\}\}', '', s, count=1)

for retired in ('GAME LAUNCHER','START HUD','STOP HUD','EVOLUTION STATUS'):
    if retired in s:
        raise SystemExit(f'Build41: retired feature remains: {retired}')

# Required owner-facing functionality must remain.
for required in ('COPY', 'GEMINI CONVERSATION', 'gemini-key-status', 'ASK GEMINI'):
    # gemini-key-status lives in repository, checked separately below.
    if required == 'gemini-key-status':
        continue
    if required not in s:
        raise SystemExit(f'Build41 regression: UI feature missing: {required}')

main.write_text(s)

rs = repo.read_text()
for required in (
    'djaeger-ai gemini-key-status',
    'djaeger-ai gemini-key-stdin',
    'djaeger-ai gemini-key-delete',
    'djaeger-ai gemini-chat-stdin',
    'djaeger-ai gemini-chat-clear',
    'djaeger-ai mode '
):
    if required not in rs:
        raise SystemExit(f'Build41 regression: trusted bridge missing: {required}')
# No APK-side sysfs writes are allowed.
if re.search(r'(echo\s+[^\n]*>\s*/sys/|tee\s+/sys/|settings put|setprop|force-stop|iptables|ip6tables|nft )', rs):
    raise SystemExit('Build41: repository mutation path detected')

# Remove implementation components for the four retired features so they are not merely hidden.
for dead in ('GameLauncherActivity.kt', 'DjaegerHudService.kt'):
    p = pkg / dead
    if p.exists():
        p.unlink()

# Strip only permissions/components that existed solely for Game Launcher/HUD.
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
ANDROID = '{http://schemas.android.com/apk/res/android}'
tree = ET.parse(manifest)
root = tree.getroot()
for child in list(root):
    if child.tag == 'uses-permission':
        name = child.attrib.get(ANDROID+'name','')
        if name in {
            'android.permission.SYSTEM_ALERT_WINDOW',
            'android.permission.PACKAGE_USAGE_STATS',
            'android.permission.RECEIVE_BOOT_COMPLETED',
            'android.permission.FOREGROUND_SERVICE'
        }:
            root.remove(child)
# Remove app components whose names clearly belong to retired launcher/HUD support.
app = root.find('application')
if app is None:
    raise SystemExit('Build41: application missing')
for child in list(app):
    name = child.attrib.get(ANDROID+'name','')
    if any(x in name for x in ('GameLauncherActivity','DjaegerHudService','BootReceiver')):
        app.remove(child)
# Queries were for launcher discovery; remove if present.
for child in list(root):
    if child.tag == 'queries':
        root.remove(child)

tree.write(manifest, encoding='unicode', xml_declaration=True)

# Final static invariants.
ms = manifest.read_text()
for forbidden in ('SYSTEM_ALERT_WINDOW','PACKAGE_USAGE_STATS','RECEIVE_BOOT_COMPLETED','FOREGROUND_SERVICE','GameLauncherActivity','DjaegerHudService'):
    if forbidden in ms:
        raise SystemExit(f'Build41 manifest regression: {forbidden}')
if 'android.intent.category.LAUNCHER' not in ms:
    raise SystemExit('Build41: main launcher activity missing')

print('Build 41 applied: v0.12.1 compact UI + latest DJAEGER-AI sync; launcher/HUD/evolution controls removed')
