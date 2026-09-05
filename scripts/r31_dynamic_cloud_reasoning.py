#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12310',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r31"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r30 • HUMAN STRATEGY','CONTROL CENTER • v0.12.1-r31 • DYNAMIC CLOUD REASONING',1).replace('v0.12.1-r30','v0.12.1-r31')

old='''    val humanStrategy="BAHASA MANUSIA\\n"+
        "$sourceHuman memilih untuk $actionHuman. "+
        "Rencana resource: CPU little ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz, "+
        "CPU big ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz, dan GPU ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz. "+
        "Tujuannya menjaga frame pacing dan performa berkelanjutan tanpa perubahan yang tidak diperlukan. "+
        "Local AI tetap menjadi validator dan executor-side safety authority.$confidenceNote"'''
new='''    // R31: show the narrative actually published by the active reasoning source.
    // No extra API/root call is made: TEXT already arrives in the atomic cc_snapshot.
    val publishedThoughtText=thoughtField(s.thoughts,"TEXT").trim()
    val cloudNarrativeFresh=thoughtSource in setOf("GEMINI","GROQ","CLOUDFLARE") && !cloudStale && publishedThoughtText.isNotBlank()
    val localNarrativeFresh=thoughtSource=="LOCAL AI" && publishedThoughtText.isNotBlank()
    val fallbackHuman="$sourceHuman memilih untuk $actionHuman. "+
        "Rencana resource: CPU little ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz, "+
        "CPU big ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz, dan GPU ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz.$confidenceNote"
    val humanStrategy=when{
        cloudNarrativeFresh->"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"
        localNarrativeFresh->"PEMIKIRAN LOCAL AI\\n$publishedThoughtText"
        else->"BAHASA MANUSIA\\n$fallbackHuman"
    }'''
assert old in ms, 'R31 R30 humanStrategy template anchor missing'
ms=ms.replace(old,new,1)

# Ensure the old repetitive boilerplate is gone from the generated UI.
assert 'Tujuannya menjaga frame pacing dan performa berkelanjutan tanpa perubahan yang tidak diperlukan.' not in ms
assert 'Local AI tetap menjadi validator dan executor-side safety authority.$confidenceNote' not in ms
# Dynamic narrative must come only from module-published Thoughts TEXT.
assert 'val publishedThoughtText=thoughtField(s.thoughts,"TEXT").trim()' in ms
assert 'cloudNarrativeFresh' in ms
assert '"PEMIKIRAN $thoughtSource\\n$publishedThoughtText"' in ms
assert '"PEMIKIRAN LOCAL AI\\n$publishedThoughtText"' in ms
# Existing structured strategy and provider truth must remain intact.
assert 'val providerLines="Active now: $activeNow\\nCloud active: $activeCloud\\nStrategy: $strategySource"' in ms
assert 'STRATEGI\\n' in ms
assert 'Validasi Local AI: ${s.strategy.validation.ifBlank{"—"}}' in ms
assert 'BoxCard("THOUGHTS", providerLines+"\\n\\n"+humanStrategy+"\\n\\n"+technicalStrategy, true)' in ms
m.write_text(ms)

print('R31_DYNAMIC_CLOUD_NARRATIVE=MODULE_PUBLISHED_TEXT')
print('R31_TEMPLATE_BOILERPLATE=REMOVED')
print('R31_EXTRA_API_CALLS=0')
print('R31_EXTRA_ROOT_POLLS=0')
print('R31_PROVIDER_TRUTH=PRESERVED')
print('R31_LOCAL_VALIDATOR=VISIBLE_UNCHANGED')
