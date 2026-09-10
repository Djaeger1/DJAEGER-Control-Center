from pathlib import Path
import xml.etree.ElementTree as ET

pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Monitoring Edition is intentionally a single-activity application. Remove all
# historical Game Turbo/HUD/control Kotlin classes so no dormant code path can
# start services, launch games, change modes, or mutate hardware.
for f in pkg.glob('*.kt'):
    if f.name != 'MainActivity.kt':
        f.unlink()

# Keep only MainActivity as an app component. This removes every legacy service,
# receiver, provider and launcher activity inherited from the old gaming branch.
# ProfileInstaller's receiver is explicitly removed at manifest-merge time;
# it is unnecessary for this tiny monitoring dashboard and otherwise carries the
# android.permission.DUMP receiver permission into the merged manifest.
manifest = Path('app/src/main/AndroidManifest.xml')
ANDROID = 'http://schemas.android.com/apk/res/android'
TOOLS = 'http://schemas.android.com/tools'
ET.register_namespace('android', ANDROID)
ET.register_namespace('tools', TOOLS)
tree = ET.parse(manifest)
root = tree.getroot()
android_name = '{%s}name' % ANDROID
app = root.find('application')
if app is None:
    raise SystemExit('Build39: manifest application missing')
for child in list(app):
    tag = child.tag.split('}')[-1]
    if tag in {'activity','activity-alias','service','receiver','provider'}:
        name = child.attrib.get(android_name, '')
        keep = tag == 'activity' and name in {'.MainActivity','com.djaeger.controlcenter.MainActivity'}
        if not keep:
            app.remove(child)
ET.SubElement(app, 'receiver', {
    android_name: 'androidx.profileinstaller.ProfileInstallReceiver',
    '{%s}node' % TOOLS: 'remove'
})
tree.write(manifest, encoding='unicode', xml_declaration=True)

# Final source audit: single activity, read-only telemetry only.
files = list(pkg.glob('*.kt'))
if [f.name for f in files] != ['MainActivity.kt']:
    raise SystemExit('Build39: unexpected Kotlin source set')
s = files[0].read_text()
for forbidden in [
    'djaeger-ai mode ', 'djaeger-ai policy-intent', 'native_write_plan',
    'settings put', 'setprop', 'force-stop', 'iptables', 'ip6tables', 'nft ',
    'TYPE_APPLICATION_OVERLAY', 'startForegroundService(', 'startService(',
    'WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY', 'echo 0 >', 'echo 1 >'
]:
    if forbidden in s:
        raise SystemExit(f'Build39 monitoring-only violation: {forbidden}')

print('Build 39 single-activity monitoring hardening applied')
