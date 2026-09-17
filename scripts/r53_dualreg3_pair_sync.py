from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'

m=main.read_text(); rd=reader.read_text(); r=repo.read_text()
old_contract='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'
new_contract='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_DUALREG3_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1_APPREBUILD4_MAXVALUE1'

# Synchronization metadata only; no Overview layout/card order changes.
m=m.replace(old_contract,new_contract)
rd=rd.replace(old_contract,new_contract)

# Current matched module/APK version pair.
m=m.replace('syncModule=="129637"','syncModule=="129652"')
m=m.replace('syncCc=="12261"','syncCc=="12262"')
m=m.replace('VC129637 / VC12261','VC129652 / VC12262')
rd=rd.replace("MODULE_VERSION_CODE='129637'","MODULE_VERSION_CODE='129652'")
rd=rd.replace("CONTROL_CENTER_VERSION_CODE='12261'","CONTROL_CENTER_VERSION_CODE='12262'")

# Where the UI exposes pair metadata, publish the explicit registry semantics.
rd=rd.replace("DUAL_REGISTRY='ENFORCED'","DUAL_REGISTRY='DUALREG3_MANUAL_SEPARATE'")

main.write_text(m); reader.write_text(rd); repo.write_text(r)

M=main.read_text(); RD=reader.read_text(); R=repo.read_text()
assert new_contract in M and new_contract in RD
assert 'syncModule=="129652"' in M
assert 'syncCc=="12262"' in M
assert "MODULE_VERSION_CODE='129652'" in RD
assert "CONTROL_CENTER_VERSION_CODE='12262'" in RD
assert "DUAL_REGISTRY='DUALREG3_MANUAL_SEPARATE'" in RD
assert 'GAME REGISTRY • MANUAL' in M and 'APP REGISTRY • MANUAL' in M
assert 'djaeger-game-registry add-stdin' in R and 'djaeger-app-registry add-stdin' in R
print('DUALREG3_PAIR_SYNC=PASS')
print('MODULE_VC=129652')
print('CONTROL_CENTER_VC=12262')
print('OVERVIEW_LAYOUT_CHANGE=NONE')
