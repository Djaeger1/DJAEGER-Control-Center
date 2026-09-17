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
    'versionCode = 5261925',
    'version_code',
)
replace(
    'app/build.gradle.kts',
    'versionName = "1.9"',
    'versionName = "526-SHADOW4-LSPOSED192-MENU1"',
    'version_name',
)
replace(
    'app/build.gradle.kts',
    'base.archivesName.set("FacebookAppAdsRemover-v${android.defaultConfig.versionName}")',
    'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-526-SHADOW4-LSPosed192-MENU1")',
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

# Restore an ordinary exported launcher activity. The first LSPosed192 build was
# intentionally hook-only (the legacy source had no Activity), which made MIUI's
# Open button and the launcher entry unavailable. This UI is framework-only and
# does NOT depend on libxposed API 101, so it remains compatible with LSPosed 1.9.2.
activity_manifest = '''
        <activity
            android:name="tn.loukious.facebookappadsremover.LegacyMainActivity"
            android:exported="true"
            android:label="DJAEGER Facebook Ad Shield 526 SHADOW4">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
'''
if 'tn.loukious.facebookappadsremover.LegacyMainActivity' not in s:
    if '</application>' not in s:
        raise SystemExit('PATCH_FAIL launcher_activity: application close tag missing')
    s = s.replace('</application>', activity_manifest + '\n    </application>', 1)
manifest.write_text(s)
print('PATCH_OK manifest_branding_launcher')

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

# Legacy-compatible settings/status screen. Filtering remains always-on while
# the module is enabled and scoped to Facebook in LSPosed; this avoids fake
# switches whose preferences could not safely cross the old Xposed boundary.
java_dir = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover'
java_dir.mkdir(parents=True, exist_ok=True)
(java_dir / 'LegacyMainActivity.java').write_text(r'''package tn.loukious.facebookappadsremover;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public final class LegacyMainActivity extends Activity {
    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private TextView text(String value, float sp, int color) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setLineSpacing(0f, 1.12f);
        return v;
    }

    private View card(String title, String body) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(18), dp(16), dp(18), dp(16));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(247, 249, 252));
        bg.setCornerRadius(dp(16));
        bg.setStroke(dp(1), Color.rgb(222, 229, 238));
        box.setBackground(bg);
        TextView t = text(title, 16f, Color.rgb(15, 52, 96));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        box.addView(t);
        TextView b = text(body, 14f, Color.rgb(55, 65, 81));
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, -2);
        bp.topMargin = dp(7);
        box.addView(b, bp);
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1, -2);
        cp.topMargin = dp(12);
        box.setLayoutParams(cp);
        return box;
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(7, 39, 82));

        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(22), dp(20), dp(30));
        root.setBackgroundColor(Color.WHITE);
        scroll.addView(root, new ScrollView.LayoutParams(-1, -2));

        TextView title = text("DJAEGER Facebook Ad Shield 526", 24f, Color.rgb(11, 78, 162));
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        root.addView(title);
        TextView sub = text("SHADOW4 • LSPosed 1.9.2 compatibility build", 14f, Color.rgb(88, 101, 118));
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(-1, -2);
        sp.topMargin = dp(4);
        root.addView(sub, sp);

        TextView active = text("●  AD SHIELD READY", 16f, Color.rgb(18, 128, 74));
        active.setTypeface(null, android.graphics.Typeface.BOLD);
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(-1, -2);
        ap.topMargin = dp(20);
        root.addView(active, ap);

        root.addView(card("Target", "Facebook com.facebook.katana\nValidated target: 526.1.0.66.75\nXposed compatibility: legacy API 93 / LSPosed 1.9.2"));
        root.addView(card("News Feed protection", "Structural GraphQL feed filtering\nSponsored / Promotion / Advertisement category guard\nLitho component guard\nLate feed / sponsored-pool fallback"));
        root.addView(card("Operation", "Filtering is always ON while this module is enabled in LSPosed and scoped to Facebook. No DNS blocking is used for Facebook feed ads."));

        Button fb = new Button(this);
        fb.setText("BUKA FACEBOOK");
        fb.setAllCaps(false);
        fb.setTextSize(15f);
        fb.setOnClickListener(v -> {
            Intent i = getPackageManager().getLaunchIntentForPackage("com.facebook.katana");
            if (i != null) startActivity(i);
        });
        LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(-1, dp(52));
        fp.topMargin = dp(18);
        root.addView(fb, fp);

        Button info = new Button(this);
        info.setText("INFO APLIKASI / SCOPE");
        info.setAllCaps(false);
        info.setTextSize(15f);
        info.setOnClickListener(v -> {
            Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName()));
            startActivity(i);
        });
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(-1, dp(52));
        ip.topMargin = dp(8);
        root.addView(info, ip);

        TextView note = text("Catatan: versi ini sengaja memakai UI Android biasa agar tombol Buka bekerja tanpa membutuhkan Modern Xposed API 101.", 12f, Color.rgb(107, 114, 128));
        note.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(-1, -2);
        np.topMargin = dp(18);
        root.addView(note, np);

        setContentView(scroll);
    }
}
''')
print('PATCH_OK legacy_menu_activity')

# Guardrails: this build MUST remain a legacy module for the user's LSPosed 1.9.2.
manifest_text = manifest.read_text()
gradle_text = (ROOT / 'app/build.gradle.kts').read_text()
xposed_init = ROOT / 'app/src/main/assets/xposed_init'
assert 'xposedminversion' in manifest_text and 'android:value="93"' in manifest_text
assert 'LegacyMainActivity' in manifest_text and 'android.intent.category.LAUNCHER' in manifest_text
assert 'com.github.deltazefiro:XposedBridge:main-SNAPSHOT' in gradle_text
assert xposed_init.exists()
assert not (ROOT / 'app/src/main/resources/META-INF/xposed/module.prop').exists()
assert (java_dir / 'LegacyMainActivity.java').exists()
print('LEGACY_XPOSED93_MENU_GUARD_PASS')
print('SHADOW4_LSPOSED192_MENU_PATCH_PASS')
