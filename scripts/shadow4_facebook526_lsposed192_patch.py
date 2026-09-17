from pathlib import Path

ROOT = Path('.')


def replace(path, old, new, label):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'PATCH_FAIL {label}: pattern not found in {path}')
    p.write_text(s.replace(old, new))
    print(f'PATCH_OK {label}')

# Keep the legacy Xposed API source/namespace intact, only give the APK its own
# install identity so it can coexist with SHADOW3 and the modern SHADOW4 build.
replace(
    'app/build.gradle.kts',
    'applicationId = "tn.loukious.facebookappadsremover"',
    'applicationId = "com.djaeger.facebookadshield526.shadow4.legacy"',
    'application_id',
)
replace(
    'app/build.gradle.kts',
    'versionCode = 10',
    'versionCode = 5261924',
    'version_code',
)
replace(
    'app/build.gradle.kts',
    'versionName = "1.9"',
    'versionName = "526-SHADOW4-LSPOSED192"',
    'version_name',
)
replace(
    'app/build.gradle.kts',
    'base.archivesName.set("FacebookAppAdsRemover-v${android.defaultConfig.versionName}")',
    'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-526-SHADOW4-LSPosed192")',
    'archive_name',
)

replace(
    'app/src/main/res/values/strings.xml',
    '<string name="app_name">Facebook App Ads Remover</string>',
    '<string name="app_name">DJAEGER Facebook Ad Shield 526 SHADOW4</string>',
    'app_name',
)

manifest = ROOT / 'app/src/main/AndroidManifest.xml'
s = manifest.read_text()
s = s.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/ic_djaeger_shield"')
s = s.replace('android:roundIcon="@mipmap/ic_launcher_round"', 'android:roundIcon="@drawable/ic_djaeger_shield"')
s = s.replace(
    'android:value="An Xposed module that removes ads from the Facebook app."',
    'android:value="DJAEGER SHADOW4 legacy build for LSPosed 1.9.2 / Xposed API 93. Structural GraphQL/Litho feed guards for Facebook 526.1.0.66.75."',
)
manifest.write_text(s)
print('PATCH_OK manifest_branding')

# Distinct build marker; the actual filtering remains structural and does not
# hard-code obfuscated Facebook class names.
replace(
    'app/src/main/java/tn/loukious/facebookappadsremover/Patches.kt',
    'fb576_structural_component_guard_v1_2026_08_29',
    'fb526_shadow4_legacy_structural_guard_v1_2026_09_18',
    'build_marker',
)

# Strengthen the master feed classifier for older 526 cohorts without touching
# safe containers (FB_SHORTS / MULTI_FB_STORIES_TRAY are separately protected).
p = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/Patches.kt'
s = p.read_text()
needle = '''private val FEED_AD_SIGNAL_TOKENS = listOf(\n    "sponsored",\n    "promotion",'''
replacement = '''private val FEED_AD_SIGNAL_TOKENS = listOf(\n    "sponsored",\n    "sponsored_data",\n    "promoted",\n    "advertisement",\n    "promotion",'''
if needle not in s:
    raise SystemExit('PATCH_FAIL fb526_signal_tokens: anchor not found')
s = s.replace(needle, replacement, 1)
p.write_text(s)
print('PATCH_OK fb526_signal_tokens')

# DJAEGER shield vector: avoids the generic green Android icon in LSPosed.
drawable = ROOT / 'app/src/main/res/drawable'
drawable.mkdir(parents=True, exist_ok=True)
(drawable / 'ic_djaeger_shield.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>\n<vector xmlns:android="http://schemas.android.com/apk/res/android"\n    android:width="48dp"\n    android:height="48dp"\n    android:viewportWidth="48"\n    android:viewportHeight="48">\n    <path\n        android:fillColor="#0B4EA2"\n        android:pathData="M24,2 L42,9 L40,29 C38,38 31,43 24,46 C17,43 10,38 8,29 L6,9 Z"/>\n    <path\n        android:fillColor="#FFFFFF"\n        android:pathData="M16,13 L25,13 C33,13 37,18 37,24 C37,31 32,35 25,35 L16,35 Z M21,18 L21,30 L25,30 C29,30 32,28 32,24 C32,20 29,18 25,18 Z"/>\n    <path\n        android:fillColor="#5DB8FF"\n        android:pathData="M24,5 L38,10 L36.8,14 L24,9 L11.2,14 L10,10 Z"/>\n</vector>\n''')
print('PATCH_OK djaeger_icon')

# Guardrails: this build MUST remain a legacy module for the user's LSPosed 1.9.2.
manifest_text = manifest.read_text()
gradle_text = (ROOT / 'app/build.gradle.kts').read_text()
xposed_init = ROOT / 'app/src/main/assets/xposed_init'
assert 'xposedminversion' in manifest_text and 'android:value="93"' in manifest_text
assert 'com.github.deltazefiro:XposedBridge:main-SNAPSHOT' in gradle_text
assert xposed_init.exists()
assert not (ROOT / 'app/src/main/resources/META-INF/xposed/module.prop').exists()
print('LEGACY_XPOSED93_GUARD_PASS')
print('SHADOW4_LSPOSED192_PATCH_PASS')
