from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); rd=reader.read_text(); b=build.read_text()

# Pair-only sync for CLOUDFREEZE1 module. No UI behavior/layout changes here.
b=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12264',b,count=1)
b=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r2-dualreg3-manualapp1-hcc1-feedback4-ui1-cloudfreeze1-matched"',b,count=1)
m=m.replace('syncModule=="129653"','syncModule=="129654"')
m=m.replace('syncCc=="12263"','syncCc=="12264"')
m=m.replace('VC129653 / VC12263','VC129654 / VC12264')
rd=rd.replace("MODULE_VERSION_CODE='129653'","MODULE_VERSION_CODE='129654'")
rd=rd.replace("CONTROL_CENTER_VERSION_CODE='12263'","CONTROL_CENTER_VERSION_CODE='12264'")

main.write_text(m); reader.write_text(rd); build.write_text(b)

M=main.read_text(); RD=reader.read_text(); B=build.read_text()
assert 'versionCode = 12264' in B and 'cloudfreeze1-matched' in B
assert 'syncModule=="129654"' in M and 'syncCc=="12264"' in M
assert "MODULE_VERSION_CODE='129654'" in RD and "CONTROL_CENTER_VERSION_CODE='12264'" in RD
# Requested UI fixes from r54 must remain intact.
assert 'GameTitlePink=Color(0xFFFF8CC6)' in M and 'color=GameTitlePink' in M
assert 'AppTitleLightBlue=Color(0xFF7DD3FC)' in M and 'color=AppTitleLightBlue' in M
assert 'visibleComfortPreset=="BASELINE"' in M and 'visibleComfortPreset=="COOL_STABLE"' in M
assert 'delay(900)' in M and M.count('HccFeedbackButton(')>=5
print('CLOUDFREEZE1_PAIR=PASS')
print('PAIR=VC129654+VC12264')
print('UI_BEHAVIOR_CHANGE=NONE_BEYOND_R54')
