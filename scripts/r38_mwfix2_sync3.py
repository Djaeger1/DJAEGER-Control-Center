from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); b=build.read_text()

# Matched Control Center identity for module MWFIX2 vc129629.
assert 'versionCode = 12255' in b
assert 'versionName = "0.12.1-rebuild3-lang3-mwfix1-math1-sync2"' in b
b=b.replace('versionCode = 12255','versionCode = 12256',1)
b=b.replace('versionName = "0.12.1-rebuild3-lang3-mwfix1-math1-sync2"','versionName = "0.12.1-rebuild3-lang3-mwfix2-math1-sync3"',1)

# Header identity only; no card removal or backend path change.
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX1 • MATH1' in m
m=m.replace('CONTROL CENTER • REBUILD3 • LANG3 • MWFIX1 • MATH1','CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • MATH1',1)

# Fix the long-standing compact label bug: old code mapped every MWFIX1 build
# to LANG2 merely because raw.contains("MWFIX1") matched first.
old='''private fun compactModuleVersion(raw:String):String=when{
    raw.contains("MWFIX1",true)->"v12.9.50 • REBUILD3 • LANG2 • MWFIX1"
    raw.contains("REBUILD3-LANG2",true)->"v12.9.50 • REBUILD3 • LANG2"
    raw.contains("REBUILD3",true)->"v12.9.50 • REBUILD3"
    else->raw
}'''
new='''private fun compactModuleVersion(raw:String):String=when{
    raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX2 • MATH1"
    raw.contains("MWFIX1",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)->"v12.9.50 • REBUILD3 • LANG3 • MWFIX1 • MATH1"
    raw.contains("MWFIX1",true)&&raw.contains("LANG2",true)->"v12.9.50 • REBUILD3 • LANG2 • MWFIX1"
    raw.contains("REBUILD3-LANG2",true)->"v12.9.50 • REBUILD3 • LANG2"
    raw.contains("REBUILD3",true)->"v12.9.50 • REBUILD3"
    else->raw
}'''
assert old in m
m=m.replace(old,new,1)

# Match the new atomic module contract. MWFIX2 fixes producer stalls; SYNC3 is
# still a read-only presentation consumer and does not gain hardware authority.
old='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX1_MATH1_SYNC1"&&syncModule=="129628"&&syncCc=="12254"'
new='val syncMatched=syncContract=="REBUILD3_LANG3_MWFIX2_MATH1_SYNC3"&&syncModule=="129629"&&syncCc=="12256"'
assert old in m
m=m.replace(old,new,1)

main.write_text(m); build.write_text(b)

# Final invariants.
M=main.read_text(); B=build.read_text()
assert 'versionCode = 12256' in B
assert '0.12.1-rebuild3-lang3-mwfix2-math1-sync3' in B
assert 'CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • MATH1' in M
assert 'REBUILD3_LANG3_MWFIX2_MATH1_SYNC3' in M
assert 'syncModule=="129629"&&syncCc=="12256"' in M
assert 'raw.contains("MWFIX2",true)&&raw.contains("LANG3",true)&&raw.contains("MATH1",true)' in M
ov=M[M.index('@Composable fun Overview('):M.index('@Composable fun Session(',M.index('@Composable fun Overview('))]
p_thought=ov.index('ThoughtsCard(s)'); p_metric=ov.index('Metric("FPS"'); p_thermal=ov.index('ThermalRow(s)'); p_network=ov.index('NetworkCard(s.network)'); p_strategy=ov.index('StrategyCard(s)')
assert p_thought < p_metric < p_thermal < p_network < p_strategy
assert 'AGENT_WINNER' not in M and 'LOCAL AI' not in M
print('MWFIX2_SYNC3_CC_PATCH=PASS')
print('COMPACT_MODULE_LANG3_IDENTITY=PASS')
print('MATCHED_MODULE_VC=129629')
print('CONTROL_CENTER_VC=12256')
print('OVERVIEW_ORDER_PRESERVED=PASS')
