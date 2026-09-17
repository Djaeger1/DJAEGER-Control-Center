from pathlib import Path

ROOT = Path('.')


def replace(path, old, new, label, count=0):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'PATCH_FAIL {label}: pattern not found in {path}')
    if count:
        s = s.replace(old, new, count)
    else:
        s = s.replace(old, new)
    p.write_text(s)
    print(f'PATCH_OK {label}')

# Install identity / version
replace('app/build.gradle.kts', 'applicationId = "tn.loukious.facebookappadsremover"',
        'applicationId = "com.djaeger.facebookadshield526.shadow4.legacy"', 'application_id')
replace('app/build.gradle.kts', 'versionCode = 10', 'versionCode = 5261926', 'version_code')
replace('app/build.gradle.kts', 'versionName = "1.9"',
        'versionName = "526-SHADOW4-LSPOSED192-MENU2-MPSAFE1"', 'version_name')
replace('app/build.gradle.kts',
        'base.archivesName.set("FacebookAppAdsRemover-v${android.defaultConfig.versionName}")',
        'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-526-SHADOW4-LSPosed192-MENU2-MPSAFE1")',
        'archive_name')
replace('app/src/main/res/values/strings.xml',
        '<string name="app_name">Facebook App Ads Remover</string>',
        '<string name="app_name">DJAEGER Facebook Ad Shield 526 SHADOW4</string>', 'app_name')

# Manifest branding + launcher activity
manifest = ROOT / 'app/src/main/AndroidManifest.xml'
s = manifest.read_text()
s = s.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/ic_djaeger_shield"')
s = s.replace('android:roundIcon="@mipmap/ic_launcher_round"', 'android:roundIcon="@drawable/ic_djaeger_shield"')
s = s.replace(
    'android:value="An Xposed module that removes ads from the Facebook app."',
    'android:value="DJAEGER SHADOW4 for Facebook 526 / LSPosed 1.9.2. Marketplace network rewrite disabled for 526 compatibility."',
)
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
    s = s.replace('</application>', activity_manifest + '\n    </application>', 1)
manifest.write_text(s)
print('PATCH_OK manifest_branding_launcher')

# Build marker + older 526 sponsored signals
replace('app/src/main/java/tn/loukious/facebookappadsremover/Patches.kt',
        'fb576_structural_component_guard_v1_2026_08_29',
        'fb526_shadow4_legacy_structural_guard_mpsafe1_2026_09_18', 'build_marker')
p = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/Patches.kt'
s = p.read_text()
needle = '''private val FEED_AD_SIGNAL_TOKENS = listOf(\n    "sponsored",\n    "promotion",'''
replacement = '''private val FEED_AD_SIGNAL_TOKENS = listOf(\n    "sponsored",\n    "sponsored_data",\n    "promoted",\n    "advertisement",\n    "promotion",'''
if needle not in s:
    raise SystemExit('PATCH_FAIL fb526_signal_tokens')
s = s.replace(needle, replacement, 1)

# Facebook 526 safety fix:
# The legacy Marketplace networking guard rewrites the *organic* Marketplace
# HomeFeed request variables (shouldSkipAdRequest / shouldSkipBoostedListingAdRequest).
# That contract was developed against newer Facebook builds. On 526 it can make
# the entire Marketplace QueryRenderer fail with the generic "unexpected error"
# page. Keep the ad-specific Marketplace Litho render block, but DO NOT hook or
# rewrite the RN Networking module on 526.
old_query_install = '''        runCatching { installMarketplaceAdsQueryBlock(classLoader, bridge) }\n            .onFailure { Log.w(TAG, "Failed to install Marketplace ads query block", it) }'''
new_query_install = '''        Log.i(TAG, "MARKETPLACE_NET_GUARD_DISABLED_FB526: preserving organic Marketplace requests")'''
if old_query_install not in s:
    raise SystemExit('PATCH_FAIL marketplace_query_install_anchor')
s = s.replace(old_query_install, new_query_install, 1)
p.write_text(s)
print('PATCH_OK marketplace_query_rewrite_disabled')

# Prevent the previously resolved/cached Networking-module hook from being
# restored before the full scan. This is essential because its cache lives in
# the Facebook process and can survive a module APK update.
module = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/Module.java'
m = module.read_text()
if 'loadCachedMarketplaceNetGuard(application);' not in m:
    raise SystemExit('PATCH_FAIL cached_marketplace_load_anchor')
m = m.replace('loadCachedMarketplaceNetGuard(application);',
              'debugLogInfo("MARKETPLACE_NET_GUARD_DISABLED_FB526: cached install skipped");', 1)
if 'retryCachedMarketplaceNetGuard(classLoader);' not in m:
    raise SystemExit('PATCH_FAIL cached_marketplace_retry_anchor')
m = m.replace('retryCachedMarketplaceNetGuard(classLoader);',
              'debugLogInfo("MARKETPLACE_NET_GUARD_DISABLED_FB526: retry skipped");')
m = m.replace('saveMarketplaceNetGuardCache();',
              'debugLogInfo("MARKETPLACE_NET_GUARD_DISABLED_FB526: cache save skipped");')
module.write_text(m)
print('PATCH_OK marketplace_cached_net_guard_disabled')

# DJAEGER shield icon
drawable = ROOT / 'app/src/main/res/drawable'
drawable.mkdir(parents=True, exist_ok=True)
(drawable / 'ic_djaeger_shield.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp" android:height="48dp"
    android:viewportWidth="48" android:viewportHeight="48">
    <path android:fillColor="#0B4EA2" android:pathData="M24,2 L42,9 L40,29 C38,38 31,43 24,46 C17,43 10,38 8,29 L6,9 Z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M16,13 L25,13 C33,13 37,18 37,24 C37,31 32,35 25,35 L16,35 Z M21,18 L21,30 L25,30 C29,30 32,28 32,24 C32,20 29,18 25,18 Z"/>
    <path android:fillColor="#5DB8FF" android:pathData="M24,5 L38,10 L36.8,14 L24,9 L11.2,14 L10,10 Z"/>
</vector>
''')
print('PATCH_OK djaeger_icon')

# Framework-only status/menu activity (no Modern Xposed API dependency)
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
    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
    private TextView text(String value, float sp, int color) {
        TextView v = new TextView(this); v.setText(value); v.setTextSize(sp); v.setTextColor(color); v.setLineSpacing(0f, 1.12f); return v;
    }
    private View card(String title, String body) {
        LinearLayout box = new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(dp(18),dp(16),dp(18),dp(16));
        GradientDrawable bg = new GradientDrawable(); bg.setColor(Color.rgb(247,249,252)); bg.setCornerRadius(dp(16)); bg.setStroke(dp(1),Color.rgb(222,229,238)); box.setBackground(bg);
        TextView t=text(title,16f,Color.rgb(15,52,96)); t.setTypeface(null,android.graphics.Typeface.BOLD); box.addView(t);
        TextView b=text(body,14f,Color.rgb(55,65,81)); LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,-2); bp.topMargin=dp(7); box.addView(b,bp);
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,-2); cp.topMargin=dp(12); box.setLayoutParams(cp); return box;
    }
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state); getWindow().setStatusBarColor(Color.rgb(7,39,82));
        ScrollView scroll=new ScrollView(this); LinearLayout root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(20),dp(22),dp(20),dp(30)); root.setBackgroundColor(Color.WHITE); scroll.addView(root,new ScrollView.LayoutParams(-1,-2));
        TextView title=text("DJAEGER Facebook Ad Shield 526",24f,Color.rgb(11,78,162)); title.setTypeface(null,android.graphics.Typeface.BOLD); root.addView(title);
        TextView sub=text("SHADOW4 • LSPosed 1.9.2 • MPSAFE1",14f,Color.rgb(88,101,118)); LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,-2); sp.topMargin=dp(4); root.addView(sub,sp);
        TextView active=text("●  AD SHIELD READY",16f,Color.rgb(18,128,74)); active.setTypeface(null,android.graphics.Typeface.BOLD); LinearLayout.LayoutParams ap=new LinearLayout.LayoutParams(-1,-2); ap.topMargin=dp(20); root.addView(active,ap);
        root.addView(card("News Feed protection","Structural GraphQL filtering\nSponsored / Promotion / Advertisement category guard\nLitho + CSR / late-feed fallback"));
        root.addView(card("Marketplace compatibility","SAFE MODE ON for Facebook 526\nOrganic Marketplace network requests are left untouched.\nOnly ad-specific render guards remain active; unsafe Marketplace request rewriting is disabled."));
        root.addView(card("Target","Facebook com.facebook.katana\nValidated target: 526.1.0.66.75\nLegacy Xposed API 93 / LSPosed 1.9.2"));
        Button fb=new Button(this); fb.setText("BUKA FACEBOOK"); fb.setAllCaps(false); fb.setOnClickListener(v->{ Intent i=getPackageManager().getLaunchIntentForPackage("com.facebook.katana"); if(i!=null)startActivity(i); }); LinearLayout.LayoutParams fp=new LinearLayout.LayoutParams(-1,dp(52)); fp.topMargin=dp(18); root.addView(fb,fp);
        Button info=new Button(this); info.setText("INFO APLIKASI / SCOPE"); info.setAllCaps(false); info.setOnClickListener(v->startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:"+getPackageName())))); LinearLayout.LayoutParams ip=new LinearLayout.LayoutParams(-1,dp(52)); ip.topMargin=dp(8); root.addView(info,ip);
        TextView note=text("MPSAFE1 dibuat khusus untuk mencegah kegagalan halaman Marketplace pada Facebook 526 tanpa melemahkan filter News Feed.",12f,Color.rgb(107,114,128)); note.setGravity(Gravity.CENTER_HORIZONTAL); LinearLayout.LayoutParams np=new LinearLayout.LayoutParams(-1,-2); np.topMargin=dp(18); root.addView(note,np);
        setContentView(scroll);
    }
}
''')
print('PATCH_OK legacy_menu_activity')

# Guardrails
manifest_text = manifest.read_text()
gradle_text = (ROOT / 'app/build.gradle.kts').read_text()
assert 'xposedminversion' in manifest_text and 'android:value="93"' in manifest_text
assert 'LegacyMainActivity' in manifest_text and 'android.intent.category.LAUNCHER' in manifest_text
assert 'com.github.deltazefiro:XposedBridge:main-SNAPSHOT' in gradle_text
assert (ROOT / 'app/src/main/assets/xposed_init').exists()
assert 'MARKETPLACE_NET_GUARD_DISABLED_FB526' in p.read_text()
assert 'MARKETPLACE_NET_GUARD_DISABLED_FB526' in module.read_text()
print('LEGACY_XPOSED93_MPSAFE1_GUARD_PASS')
print('SHADOW4_LSPOSED192_MENU2_MPSAFE1_PATCH_PASS')
