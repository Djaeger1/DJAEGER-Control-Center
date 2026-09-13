from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); b=build.read_text()

# Matched Control Center identity for module ATTR1 vc129630.
assert 'versionCode = 12256' in b
assert 'versionName = "0.12.1-rebuild3-lang3-mwfix2-math1-sync3"' in b
b=b.replace('versionCode = 12256','versionCode = 12257',1)
b=b.replace('versionName = "0.12.1-rebuild3-lang3-mwfix2-math1-sync3"','versionName = "0.12.1-rebuild3-lang3-mwfix2-attr1-math1-sync4"',1)

# Header identity only. ATTR1 changes attribution/health bookkeeping in the
# matched module; Control Center remains a read-only presentation consumer.
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • MATH1' in m
m=m.replace('CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • MATH1','CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1',1)

# Compact module identity: recognize ATTR1 before generic MWFIX2.
old='''private fun compactModuleVersion(raw:String):String=when{
    raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • MATH1"'''
new='''private fun compactModuleVersion(raw:String):String=when{
    raw.contains("ATTR1",true)&&raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1"
    raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • MATH1"'''
assert old in m
m=m.replace(old,new,1)

# Exact matched contract. Do not accept mixed module/app revisions.
old='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_MATH1_SYNC3"&&syncModule=="129629"&&syncCc=="12256"'
new='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_SYNC4"&&syncModule=="129630"&&syncCc=="12257"'
assert old in m
m=m.replace(old,new,1)

main.write_text(m); build.write_text(b)

M=main.read_text(); B=build.read_text()
assert 'versionCode = 12257' in B
assert '0.12.1-rebuild3-lang3-mwfix2-attr1-math1-sync4' in B
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1' in M
assert 'REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_SYNC4' in M
assert 'syncModule=="129630"&&syncCc=="12257"' in M
assert 'raw.contains("ATTR1",true)&&raw.contains("MWFIX2",true)' in M
# Architecture invariant: no third AI brain is reintroduced.
assert 'AGENT_WINNER' not in M and 'LOCAL AI' not in M
print('ATTR1_SYNC4_CC_PATCH=PASS')
print('MATCHED_MODULE_VC=129630')
print('CONTROL_CENTER_VC=12257')
