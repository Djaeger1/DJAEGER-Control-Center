from pathlib import Path
import re
import xml.etree.ElementTree as ET

# Monitoring Edition uses only framework android.* widgets plus Kotlin stdlib.
# Drop the historical AndroidX/Compose dependency graph so dormant libraries
# cannot contribute services/providers/receivers or foreground permissions.
g = Path('app/build.gradle.kts')
s = g.read_text()

# Remove the final top-level dependencies block. Historical project dependencies
# use function calls only (no nested Kotlin brace blocks), so brace matching is
# still used here rather than a broad regex.
def remove_block(text: str, keyword: str) -> str:
    m = re.search(r'(?m)^\s*' + re.escape(keyword) + r'\s*\{', text)
    if not m:
        return text
    start = m.start()
    brace = text.find('{', m.start(), m.end())
    depth = 0
    in_str = False
    esc = False
    for i in range(brace, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[:start] + '\ndependencies {\n}\n' + text[i+1:]
    raise SystemExit(f'Build41: unterminated {keyword} block')

s = remove_block(s, 'dependencies')
# Disable Compose build feature if inherited from the old UI project.
s = re.sub(r'compose\s*=\s*true', 'compose = false', s)
g.write_text(s)

# Final manifest must need no Android runtime/special permissions and expose only
# MainActivity. Use a platform theme so no AndroidX/Material resources are needed.
manifest = Path('app/src/main/AndroidManifest.xml')
ANDROID = 'http://schemas.android.com/apk/res/android'
ET.register_namespace('android', ANDROID)
tree = ET.parse(manifest)
root = tree.getroot()
app = root.find('application')
if app is None:
    raise SystemExit('Build41: manifest application missing')
for child in list(root):
    tag = child.tag.split('}')[-1]
    if tag in {'uses-permission', 'permission', 'queries'}:
        root.remove(child)
app.set('{%s}theme' % ANDROID, '@android:style/Theme.Material.NoActionBar')

# Build39 may have inserted a tools:node removal marker for a dependency that no
# longer exists. Remove every non-MainActivity app component one final time.
android_name = '{%s}name' % ANDROID
for child in list(app):
    tag = child.tag.split('}')[-1]
    if tag in {'activity','activity-alias','service','receiver','provider'}:
        name = child.attrib.get(android_name, '')
        keep = tag == 'activity' and name in {'.MainActivity','com.djaeger.controlcenter.MainActivity'}
        if not keep:
            app.remove(child)
tree.write(manifest, encoding='unicode', xml_declaration=True)

# Fail closed if historical UI dependencies or permissions survive source config.
final_g = g.read_text()
for marker in ['androidx.', 'com.google.android.material', 'compose.material', 'profileinstaller']:
    if marker in final_g:
        raise SystemExit(f'Build41: historical dependency remains: {marker}')
final_m = manifest.read_text()
for marker in ['uses-permission', '<service', '<receiver', '<provider', '<queries']:
    if marker in final_m:
        raise SystemExit(f'Build41: unexpected manifest surface remains: {marker}')

print('Build 41 minimal monitoring runtime applied')
