from pathlib import Path

ROOT = Path('control-center-r2')
MAIN = ROOT / 'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
REPO = ROOT / 'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
MAPPER = ROOT / 'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'
BUILD = ROOT / 'app/build.gradle.kts'


def replace_once(path: Path, old: str, new: str):
    s = path.read_text()
    if old not in s:
        raise SystemExit(f'missing marker in {path}: {old[:100]!r}')
    path.write_text(s.replace(old, new, 1))

# Matched identity.
replace_once(BUILD, 'versionCode = 12253', 'versionCode = 12254')
replace_once(BUILD, 'versionName = "0.12.1-rebuild3-lang2-mwfix1"', 'versionName = "0.12.1-rebuild3-lang3-mwfix1-math1-sync1"')

# Preserve the single atomic cc_snapshot reader while exposing new additive sections.
replace_once(
    MAPPER,
    '        val hermesHumanComfort: String,\n        val strategyResult: String,',
    '        val hermesHumanComfort: String,\n        val hermesLanguage: String,\n        val hermesMath: String,\n        val controlCenterSync: String,\n        val strategyResult: String,'
)
replace_once(
    MAPPER,
    '            hermesHumanComfort = s["HERMES_HUMAN_COMFORT"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),',
    '            hermesHumanComfort = s["HERMES_HUMAN_COMFORT"].orEmpty(),\n            hermesLanguage = s["HERMES_LANGUAGE"].orEmpty(),\n            hermesMath = s["HERMES_MATH"].orEmpty(),\n            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),\n            strategyResult = s["STRATEGY_RESULT"].orEmpty(),'
)

replace_once(
    REPO,
    'val hermesResearchV2:String="",val hermesHumanComfort:String="",val envelope:String="",',
    'val hermesResearchV2:String="",val hermesHumanComfort:String="",val hermesLanguage:String="",val hermesMath:String="",val controlCenterSync:String="",val envelope:String="",'
)
replace_once(
    REPO,
    'hermesResearchV2=mapped.hermesResearchV2,hermesHumanComfort=mapped.hermesHumanComfort,\n            envelope=mapped.envelope,',
    'hermesResearchV2=mapped.hermesResearchV2,hermesHumanComfort=mapped.hermesHumanComfort,hermesLanguage=mapped.hermesLanguage,hermesMath=mapped.hermesMath,controlCenterSync=mapped.controlCenterSync,\n            envelope=mapped.envelope,'
)

# UI identity and explicit language-engine truth.
replace_once(MAIN, 'CONTROL CENTER • REBUILD3 • LANG2 • MWFIX1', 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX1 • MATH1')
replace_once(
    MAIN,
    '    val conf=envField(s.thoughts,"CONFIDENCE")\n    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}',
    '    val conf=envField(s.thoughts,"CONFIDENCE")\n    val lang=envField(s.thoughts,"LANGUAGE").ifBlank{envField(s.hermesLanguage,"LANGUAGE").ifBlank{"id-ID"}}\n    val langEngine=envField(s.thoughts,"LANGUAGE_ENGINE").ifBlank{envField(s.hermesLanguage,"ENGINE").ifBlank{"NLG_LANG3_CONVERSATIONAL"}}\n    val text=envField(s.thoughts,"TEXT").ifBlank{"Belum ada pemikiran baru. DJAEGER sedang mengumpulkan konteks dan outcome."}'
)
replace_once(
    MAIN,
    'Confidence: ${conf.ifBlank{"—"}}%\\n$mem"',
    'Confidence: ${conf.ifBlank{"—"}}%\\nLanguage: $lang • $langEngine\\n$mem"'
)

# Extend Hermes card with read-only Math Core and matched-pair status.
replace_once(
    MAIN,
    '    val hReason=envField(s.brain,"HERMES_REASON").ifBlank{"Belum ada reasoning Hermes yang dipublikasikan module."}\n    val currentBrain=envField(s.brain,"CURRENT_BRAIN")',
    '''    val hReason=envField(s.brain,"HERMES_REASON").ifBlank{"Belum ada reasoning Hermes yang dipublikasikan module."}
    val mathState=envField(s.hermesMath,"STATE").ifBlank{"UNAVAILABLE"}
    val mathVerify=envField(s.hermesMath,"VERIFY").ifBlank{"—"}
    val mathSanity=envField(s.hermesMath,"INPUT_SANITY").ifBlank{"—"}
    val mathFrame=envField(s.hermesMath,"TARGET_FRAME_MS").ifBlank{"—"}
    val mathFpsErr=envField(s.hermesMath,"FPS_ERROR").ifBlank{"—"}
    val mathHeadroom=envField(s.hermesMath,"THERMAL_HEADROOM_C").ifBlank{"—"}
    val mathThermal=envField(s.hermesMath,"THERMAL_PRESSURE").ifBlank{"—"}
    val mathFramePressure=envField(s.hermesMath,"FRAME_PRESSURE").ifBlank{"—"}
    val mathControl=envField(s.hermesMath,"CONTROL_PRESSURE").ifBlank{"—"}
    val syncContract=envField(s.controlCenterSync,"CONTRACT").ifBlank{"UNPUBLISHED"}
    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE").ifBlank{"—"}
    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE").ifBlank{"—"}
    val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX1_MATH1_SYNC1"&&syncModule=="129628"&&syncCc=="12254"
    val currentBrain=envField(s.brain,"CURRENT_BRAIN")'''
)
replace_once(
    MAIN,
    'Reason: $hReason"\n    BoxCard("HERMES H2 • LOCAL BRAIN",body,true)',
    'Reason: $hReason\\n\\nLANG3: CONVERSATIONAL • semantic planner + continuity + anti-repeat\\nMATH1: $mathState • verify $mathVerify • sanity $mathSanity\\nTarget frame: $mathFrame ms • FPS error: $mathFpsErr\\nThermal headroom: $mathHeadroom °C • thermal/frame/control pressure: $mathThermal/$mathFramePressure/$mathControl\\nControl Center sync: ${if(syncMatched) "MATCHED" else "MISMATCH/WAITING"} • $syncContract • module vc$syncModule / app vc$syncCc"\n    BoxCard("HERMES H2 • LANG3 + MATH1",body,true)'
)

# Static invariants: presentation only, same package, no new root read path.
M = MAIN.read_text(); R = REPO.read_text(); C = MAPPER.read_text(); B = BUILD.read_text()
assert 'versionCode = 12254' in B
assert '0.12.1-rebuild3-lang3-mwfix1-math1-sync1' in B
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX1 • MATH1' in M
assert 'HERMES H2 • LANG3 + MATH1' in M
assert 'NLG_LANG3_CONVERSATIONAL' in M
assert 'HERMES_MATH' in C and 'CONTROL_CENTER_SYNC' in C and 'HERMES_LANGUAGE' in C
assert 'hermesMath=mapped.hermesMath' in R and 'controlCenterSync=mapped.controlCenterSync' in R
snap = R[R.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'):R.index('    suspend fun setUserMode', R.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){'))]
assert snap.count('ConsolidatedSnapshotReader') == 1
assert 'cat /data/adb/djaeger_ai' not in snap
assert 'AGENT_WINNER' not in M
assert 'LOCAL AI' not in M
print('LANG3_MATH1_SYNC1_PATCH=PASS')
print('ATOMIC_SNAPSHOT_SINGLE_READ=PASS')
print('PRESENTATION_ONLY_SYNC=PASS')
