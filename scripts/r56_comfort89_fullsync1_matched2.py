from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text()
rd=reader.read_text()
b=build.read_text()

# This shadow patch binds the existing VC129653/VC12263 pair to the
# backend-published COMFORT89_FULLSYNC1 semantic contract.
# It does not add hardware authority and does not touch backend/sysfs paths.

# 1) The APK must not append a second authoritative CONTROL_CENTER_SYNC block.
# Keep APK expectations separate so backend cc_snapshot remains the source of truth.
sync_header="printf '\\n__CONTROL_CENTER_SYNC__\\n'"
assert sync_header in rd, 'CONTROL_CENTER_SYNC append anchor missing'
rd=rd.replace(sync_header, "printf '\\n__CONTROL_CENTER_EXPECTATION__\\n'", 1)

# 2) Keep pair VC identity but give the APK an explicit semantic build identity.
b=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12263',b,count=1)
b=re.sub(
    r'versionName\s*=\s*"[^"]+"',
    'versionName = "0.12.1-r2-dualreg3-hcc1-feedback4-ui1-comfort89-fullsync1-matched2"',
    b,
    count=1,
)

# 3) Every existing matched gate using backend CONTROL_CENTER_SYNC must also
# validate the comfort-contract id and full synchronization route.
sync_cc='    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE")'
insert=(
    sync_cc+
    '\n    val syncGameComfort=envField(s.controlCenterSync,"GAME_COMFORT_CONTRACT")'
    '\n    val syncGameComfortRoute=envField(s.controlCenterSync,"GAME_COMFORT_SYNC")'
)
count=m.count(sync_cc)
assert count >= 3, f'expected >=3 pair gates, got {count}'
m=m.replace(sync_cc,insert)

pair_re=re.compile(r'syncModule=="129653"\s*&&\s*syncCc=="12263"')
m,n=pair_re.subn(
    'syncModule=="129653"&&syncCc=="12263"'
    '&&syncGameComfort=="COMFORT89_FULLSYNC1"'
    '&&syncGameComfortRoute=="GEMINI_HERMES_LOCAL_CLOUD_AGENT_CONTROLLER"',
    m,
)
assert n >= 3, f'expected >=3 pair conditions, got {n}'

# 4) Make the visible pair provenance truthful without changing card order/layout.
m=m.replace(
    'MATCHED • VC129653 / VC12263',
    'MATCHED • VC129653 / VC12263 • COMFORT89',
)
m=m.replace(
    'Control Center pair: ${if(paired)"MATCHED • VC129653 / VC12263 • COMFORT89" else "CHECKING / NOT MATCHED"}',
    'Comfort contract: $syncGameComfort\\nComfort sync: $syncGameComfortRoute\\n'
    'Control Center pair: ${if(paired)"MATCHED • VC129653 / VC12263 • COMFORT89" else "CHECKING / NOT MATCHED"}',
)

main.write_text(m)
reader.write_text(rd)
build.write_text(b)

M=main.read_text(); RD=reader.read_text(); B=build.read_text()
assert 'versionCode = 12263' in B
assert 'comfort89-fullsync1-matched2' in B
assert '__CONTROL_CENTER_EXPECTATION__' in RD
assert "printf '\\n__CONTROL_CENTER_SYNC__\\n'" not in RD
assert M.count('syncGameComfort=envField(s.controlCenterSync,"GAME_COMFORT_CONTRACT")') >= 3
assert M.count('syncGameComfortRoute=envField(s.controlCenterSync,"GAME_COMFORT_SYNC")') >= 3
assert M.count('syncGameComfort=="COMFORT89_FULLSYNC1"') >= 3
assert M.count('syncGameComfortRoute=="GEMINI_HERMES_LOCAL_CLOUD_AGENT_CONTROLLER"') >= 3
assert 'MATCHED • VC129653 / VC12263 • COMFORT89' in M
assert '/sys/' not in RD
print('COMFORT89_FULLSYNC1_MATCHED2_APK_PATCH=PASS')
print('PAIR=VC129653+VC12263')
print('SEMANTIC_CONTRACT=COMFORT89_FULLSYNC1')
print('SEMANTIC_SYNC=GEMINI_HERMES_LOCAL_CLOUD_AGENT_CONTROLLER')
print('CONTROL_CENTER_SYNC_AUTHORITY=BACKEND_CC_SNAPSHOT')
print('UI_LAYOUT_REORDER=NONE')
print('HARDWARE_AUTHORITY_CHANGE=NONE')
