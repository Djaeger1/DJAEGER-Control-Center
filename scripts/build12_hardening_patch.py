from pathlib import Path

# Harden the already-applied Build 11 source without changing DJAEGER control behavior.
g = Path('app/build.gradle.kts')
s = g.read_text()
s = s.replace('versionCode = 13', 'versionCode = 14')
s = s.replace('versionName = "0.6.1-rc-ai-bridge"', 'versionName = "0.6.2-rc-ai-bridge-hardened"')
# Compose ui-tooling is useful only for previews/debug inspection and was responsible
# for merged-manifest DUMP/PreviewActivity entries in the Build 11 APK.
lines = []
for line in s.splitlines():
    if 'ui-tooling' in line and 'ui-tooling-preview' not in line:
        continue
    lines.append(line)
g.write_text('\n'.join(lines) + '\n')

m = Path('app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s = m.read_text().replace('GAMING TURBO • v0.6.1 RC • AI BRIDGE • REALTIME 1s', 'GAMING TURBO • v0.6.2 RC • AI BRIDGE HARDENED • REALTIME 1s')
s = s.replace('DJAEGER v0.6.1 RC', 'DJAEGER v0.6.2 RC')
m.write_text(s)

# Keep source manifest minimal. No INTERNET or privileged/system permissions are added.
# The workflow validates the *merged* manifest after Gradle, catching transitive manifests too.
