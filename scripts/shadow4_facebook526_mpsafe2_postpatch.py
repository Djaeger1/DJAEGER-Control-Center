from pathlib import Path

ROOT = Path('.')


def replace(path, old, new, label, count=1):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'PATCH_FAIL {label}: pattern not found in {path}')
    s = s.replace(old, new, count) if count else s.replace(old, new)
    p.write_text(s)
    print(f'PATCH_OK {label}')

# MPSAFE2 is deliberately conservative: keep the News Feed structural blocker,
# but hard-bypass every Marketplace-specific hook on Facebook 526.1.0.66.75.
# This addresses the observed pattern where Marketplace opens normally first,
# then fails after delayed DexKit-discovered Marketplace hooks are installed.

replace(
    'app/build.gradle.kts',
    'versionCode = 5261926',
    'versionCode = 5261927',
    'version_code_mpsafe2',
)
replace(
    'app/build.gradle.kts',
    'versionName = "526-SHADOW4-LSPOSED192-MENU2-MPSAFE1"',
    'versionName = "526-SHADOW4-LSPOSED192-MENU3-MPSAFE2"',
    'version_name_mpsafe2',
)
replace(
    'app/build.gradle.kts',
    'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-526-SHADOW4-LSPosed192-MENU2-MPSAFE1")',
    'base.archivesName.set("DJAEGER-Facebook-Ad-Shield-526-SHADOW4-LSPosed192-MENU3-MPSAFE2")',
    'archive_name_mpsafe2',
)

p = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/Patches.kt'
s = p.read_text()

# Distinct marker for the runtime-isolation build.
s = s.replace(
    'fb526_shadow4_legacy_structural_guard_mpsafe1_2026_09_18',
    'fb526_shadow4_legacy_structural_guard_mpsafe2_2026_09_18',
    1,
)

# 1) Never install the Marketplace Litho render nuller on Facebook 526.
old = '''        runCatching { installMarketplaceAdRenderBlock(classLoader, bridge) }\n            .onFailure { Log.w(TAG, "Failed to install Marketplace ad render block", it) }'''
new = '''        Log.i(TAG, "MARKETPLACE_HARD_BYPASS_FB526: render guard skipped")'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_render_install_anchor')
s = s.replace(old, new, 1)

# 2) MPSAFE1 already disabled Marketplace request rewriting. Keep that and also
# disable the response emitter probe so no Marketplace network path is hooked.
old = '''        runCatching { installMarketplaceFeedResponseFilter(classLoader, bridge) }\n            .onFailure { Log.w(TAG, "Failed to install Marketplace response probe", it) }'''
new = '''        Log.i(TAG, "MARKETPLACE_HARD_BYPASS_FB526: response emitter hook skipped")'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_response_install_anchor')
s = s.replace(old, new, 1)

# 3) Do not discover MarketplaceAdsPluginPack as part of the generic plugin-pack
# fallback. Keep the Reels plugin discovery that contributes to News Feed/Reels.
old = '"pluginPack" to listOf("FbShortsViewerPluginPack", "MarketplaceAdsPluginPack")'
new = '"pluginPack" to listOf("FbShortsViewerPluginPack")'
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_plugin_discovery_anchor')
s = s.replace(old, new, 1)

# 4) Remove the Marketplace-specific branch from the generic plugin-pack hook.
# Generic ad-story filtering remains intact for News Feed/Reels.
old = '''            if (isMarketplaceAdsPluginPack(param.thisObject)) {\n                Log.i(TAG, "Returning an empty plugin pack for marketplace ads (${method.declaringClass.name})")\n                param.result = arrayListOf<Any?>()\n                return\n            }\n'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_plugin_before_branch')
s = s.replace(old, '''            // MARKETPLACE_HARD_BYPASS_FB526: do not blank Marketplace plugin packs.\n''', 1)
old = '            if (isMarketplaceAdsPluginPack(param.thisObject)) return\n'
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_plugin_after_branch')
s = s.replace(old, '            // MARKETPLACE_HARD_BYPASS_FB526: no Marketplace post-filter branch.\n', 1)

# 5) Prevent the generic feed signal classifier from treating named Marketplace
# model/type strings as ad evidence. This leaves Marketplace data native while
# preserving the same News Feed structural hooks for non-Marketplace models.
old = '''    private fun isLikelyAdTypeName(value: String?): Boolean {\n        if (value == null) return false\n        if (value.contains("QuickPromotion", ignoreCase = true)) return true\n        return isAdSignalText(value)\n    }'''
new = '''    private fun isLikelyAdTypeName(value: String?): Boolean {\n        if (value == null) return false\n        if (value.contains("Marketplace", ignoreCase = true)) return false\n        if (value.contains("QuickPromotion", ignoreCase = true)) return true\n        return isAdSignalText(value)\n    }'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_type_bypass_anchor')
s = s.replace(old, new, 1)

old = '''        val type = value.javaClass\n        if (isAdSignalText(type.name)) return true'''
new = '''        val type = value.javaClass\n        if (type.name.contains("Marketplace", ignoreCase = true)) return false\n        if (isAdSignalText(type.name)) return true'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_object_bypass_anchor')
s = s.replace(old, new, 1)

old = '''    private fun isAdSignalText(value: String?): Boolean {\n        if (value.isNullOrBlank()) return false\n        val normalized = value.lowercase()\n        return FEED_AD_SIGNAL_TOKENS.any { token -> normalized.contains(token) }\n    }'''
new = '''    private fun isAdSignalText(value: String?): Boolean {\n        if (value.isNullOrBlank()) return false\n        val normalized = value.lowercase()\n        if (normalized.contains("marketplace")) return false\n        return FEED_AD_SIGNAL_TOKENS.any { token -> normalized.contains(token) }\n    }'''
if old not in s:
    raise SystemExit('PATCH_FAIL marketplace_signal_bypass_anchor')
s = s.replace(old, new, 1)

p.write_text(s)
print('PATCH_OK marketplace_hard_bypass')

# Update the framework-only menu so the installed build is unambiguous.
menu = ROOT / 'app/src/main/java/tn/loukious/facebookappadsremover/LegacyMainActivity.java'
m = menu.read_text()
m = m.replace('SHADOW4 • LSPosed 1.9.2 • MPSAFE1', 'SHADOW4 • LSPosed 1.9.2 • MPSAFE2', 1)
m = m.replace(
    'SAFE MODE ON for Facebook 526\\nOrganic Marketplace network requests are left untouched.\\nOnly ad-specific render guards remain active; unsafe Marketplace request rewriting is disabled.',
    'HARD BYPASS ON for Facebook 526\\nMarketplace network, render, response and plugin-pack hooks are disabled.\\nMarketplace is left native; News Feed filtering remains active.',
    1,
)
m = m.replace(
    'MPSAFE1 dibuat khusus untuk mencegah kegagalan halaman Marketplace pada Facebook 526 tanpa melemahkan filter News Feed.',
    'MPSAFE2 mengisolasi Marketplace sepenuhnya dari hook khusus Marketplace agar halaman tetap native dan stabil; filter News Feed tetap aktif.',
    1,
)
menu.write_text(m)
print('PATCH_OK mpsafe2_menu')

# Strong build-time guardrails: explicit Marketplace interception installs must
# be absent, while the structural News Feed machinery remains present.
out = p.read_text()
assert 'MARKETPLACE_HARD_BYPASS_FB526: render guard skipped' in out
assert 'MARKETPLACE_HARD_BYPASS_FB526: response emitter hook skipped' in out
assert 'runCatching { installMarketplaceAdRenderBlock(classLoader, bridge) }' not in out
assert 'runCatching { installMarketplaceAdsQueryBlock(classLoader, bridge) }' not in out
assert 'runCatching { installMarketplaceFeedResponseFilter(classLoader, bridge) }' not in out
assert '"pluginPack" to listOf("FbShortsViewerPluginPack", "MarketplaceAdsPluginPack")' not in out
assert 'if (isMarketplaceAdsPluginPack(param.thisObject))' not in out
assert 'GRAPHQL_FEED_UNIT_EDGE_CLASS' in out
assert 'FeedCSRCacheFilter' in out
assert 'NewsFeedFeedUnitComponent' in out
print('MPSAFE2_HARD_BYPASS_GUARD_PASS')
