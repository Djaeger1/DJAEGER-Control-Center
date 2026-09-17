from pathlib import Path

ROOT = Path('.')


def replace_once(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'PATCH_FAIL {label}: pattern not found in {path}')
    s2 = s.replace(old, new, 1)
    p.write_text(s2, encoding='utf-8')
    print(f'PATCH_OK {label}')

# Keep the mature upstream implementation, but give this experiment a separate
# package identity so it cannot overwrite the user's existing SHADOW3 module.
replace_once(
    'app/build.gradle.kts',
    'applicationId = "tn.loukious.facebookappadsremover"',
    'applicationId = "com.djaeger.facebookadshield526.shadow4"',
    'application_id',
)
replace_once(
    'app/build.gradle.kts',
    'versionCode = 16',
    'versionCode = 40',
    'version_code',
)
replace_once(
    'app/build.gradle.kts',
    'versionName = "1.15"',
    'versionName = "526-SHADOW4"',
    'version_name',
)
replace_once(
    'app/build.gradle.kts',
    'base.archivesName.set("FacebookAppAdsRemover-v${android.defaultConfig.versionName}")',
    'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-${android.defaultConfig.versionName}")',
    'archive_name',
)

strings = ROOT / 'app/src/main/res/values/strings.xml'
s = strings.read_text(encoding='utf-8')
s = s.replace('Facebook App Ads Remover', 'DJAEGER Facebook Ad Shield 526 SHADOW4')
s = s.replace(
    'Modern Xposed module for Facebook: ad-free feed, media download, account tools',
    'DJAEGER SHADOW4 compatibility build for Facebook 526. Structural News Feed ad filtering with layered fallback guards.'
)
s = s.replace(
    'Module loaded. Enable it in LSPosed for com.facebook.katana, then restart Facebook.',
    'SHADOW4 loaded. Enable only Facebook (com.facebook.katana) in LSPosed, then restart Facebook.'
)
strings.write_text(s, encoding='utf-8')
print('PATCH_OK branding_strings')

# The upstream project currently waits for a set of stable classes selected for
# FB 576 before running DexKit discovery. FB 526 can lack unrelated members of
# that probe set, which means the feed hooks never get a chance to install.
# For SHADOW4, gate discovery only on the two structural types needed by the
# classic News Feed classifier. Both are used by the actual filter itself.
targets = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/core/Targets.kt'
s = targets.read_text(encoding='utf-8')
start = s.index('    val stableClasses = listOf(')
end = s.index('    )', start) + len('    )')
replacement = '''    val stableClasses = listOf(\n        "com.facebook.graphql.model.GraphQLFeedUnitEdge",\n        "com.crossapp.graphql.facebook.enums.GraphQLFeedStoryCategory",\n    )'''
s = s[:start] + replacement + s[end:]
targets.write_text(s, encoding='utf-8')
print('PATCH_OK fb526_feed_probe_gate')

# FB 526 cohorts can expose ad-like rows as PROMOTION/ADVERTISEMENT/AD rather
# than only SPONSORED. In this dedicated ad-shield build all of those are tied
# to the master ads switch. Safe content containers remain protected by the
# FeedGuard classifier's explicit safe-container list.
news = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/hooks/NewsfeedFilterHook.kt'
s = news.read_text(encoding='utf-8')
old = '''    private val categoryPrefs = mapOf(\n        "SPONSORED" to Settings.ADS_ENABLED,\n        "PROMOTION" to Settings.FEED_THREADS,\n        "FB_SHORTS" to Settings.FEED_REELS,\n        "ENGAGEMENT" to Settings.FEED_SUGGESTIONS,\n        "ENGAGEMENT_QP" to Settings.FEED_PYMK,\n        "MULTI_FB_STORIES_TRAY" to Settings.FEED_STORIES,\n    )'''
new = '''    private val categoryPrefs = mapOf(\n        "SPONSORED" to Settings.ADS_ENABLED,\n        "PROMOTION" to Settings.ADS_ENABLED,\n        "ADVERTISEMENT" to Settings.ADS_ENABLED,\n        "AD" to Settings.ADS_ENABLED,\n        "BANNER" to Settings.ADS_ENABLED,\n        "FB_SHORTS" to Settings.FEED_REELS,\n        "ENGAGEMENT" to Settings.FEED_SUGGESTIONS,\n        "ENGAGEMENT_QP" to Settings.FEED_PYMK,\n        "MULTI_FB_STORIES_TRAY" to Settings.FEED_STORIES,\n    )'''
if old not in s:
    raise SystemExit('PATCH_FAIL fb526_ad_categories: pattern not found')
news.write_text(s.replace(old, new, 1), encoding='utf-8')
print('PATCH_OK fb526_ad_categories')

# Add a build marker visible in APK strings/log inspection.
strings = ROOT / 'app/src/main/res/values/strings.xml'
s = strings.read_text(encoding='utf-8')
marker = '    <string name="djaeger_shadow4_build">FB526_STRUCTURAL_FEED_SHADOW4</string>\n'
if marker not in s:
    s = s.replace('</resources>', marker + '</resources>')
strings.write_text(s, encoding='utf-8')
print('PATCH_OK build_marker')

# Static assertions: fail the CI build rather than silently emitting a module
# with the wrong target/scope or without the structural filter.
manifest = (ROOT / 'app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')
feed = news.read_text(encoding='utf-8')
assert 'com.facebook.katana' in manifest
assert 'GraphQLFeedUnitEdge' in feed
assert 'GraphQLFeedStoryCategory' in feed
assert 'Added stories to FUC' in feed
assert 'SPONSORED' in feed
assert 'PROMOTION' in feed
print('SHADOW4_PATCH_PASS')
