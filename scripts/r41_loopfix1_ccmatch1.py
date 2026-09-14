from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); b=build.read_text()

# Keep the module-paired app versionCode 12258. Change only the display versionName.
assert 'versionCode = 12258' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1"' in b
b=b.replace(
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1"',
    'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-ccmatch1"',
    1,
)

# The old Agent card used a historical version-name substring that current REBUILD3
# derivatives no longer contain. Match the real module/app contract published by
# __CONTROL_CENTER_SYNC__, with a strong module-version fallback only while the
# atomic sync section is not yet available during startup.
old='''    val matched=s.moduleVersion.contains("AGENT-FULL-HW-REBUILD3",true)\n    val body="Matched module: ${if(matched) "YES" else "NO — install REBUILD3 module"}\\nRole: $role'''
new='''    val syncContract=envField(s.controlCenterSync,"CONTRACT")\n    val syncModule=envField(s.controlCenterSync,"MODULE_VERSION_CODE")\n    val syncCc=envField(s.controlCenterSync,"CONTROL_CENTER_VERSION_CODE")\n    val syncKernel=envField(s.controlCenterSync,"HERMES_KERNEL")\n    val syncSysfs=envField(s.controlCenterSync,"AGENT_SYSFS")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1"&&syncModule=="129631"&&syncCc=="12258"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)\n    val matched=s.installed&&(exactMatched||identityMatched)\n    val matchText=when{exactMatched->"YES • EXACT CONTRACT";identityMatched->"YES • REBUILD3 IDENTITY";!s.installed->"NO • MODULE NOT INSTALLED";else->"CHECKING • CONTRACT NOT PUBLISHED"}\n    val body="Matched module: $matchText\\nRole: $role'''
assert old in m
m=m.replace(old,new,1)

# Show the active LOOPFIX1 lineage when present, while retaining every older mapping.
old='''private fun compactModuleVersion(raw:String):String=when{\n    raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1"'''
new='''private fun compactModuleVersion(raw:String):String=when{\n    raw.contains("LOOPFIX1",true)&&raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1 • LOOPFIX1"\n    raw.contains("CCSYNC1",true)&&raw.contains("KERNEL1",true)&&raw.contains("SYSFS1",true)->"v12.9.50 • REBUILD3 • HK1 • SYSFS1 • CCSYNC1"'''
assert old in m
m=m.replace(old,new,1)

# Header truth only; no authority/runtime behavior change.
old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1'
new_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1'
assert old_header in m
m=m.replace(old_header,new_header,1)

main.write_text(m); build.write_text(b)

M=main.read_text(); B=build.read_text()
assert 'versionCode = 12258' in B
assert 'loopfix1-ccmatch1' in B
assert 'AGENT-FULL-HW-REBUILD3' not in M
assert 'exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1"' in M
assert 'syncModule=="129631"&&syncCc=="12258"' in M
assert 'identityMatched=s.moduleVersion.contains("REBUILD3",true)' in M
assert 'YES • EXACT CONTRACT' in M
assert 'YES • REBUILD3 IDENTITY' in M
assert 'CHECKING • CONTRACT NOT PUBLISHED' in M
assert 'CCSYNC1 • LOOPFIX1' in M
print('LOOPFIX1_CCMATCH1_PATCH=PASS')
print('MATCHED_MODULE_VC=129631')
print('CONTROL_CENTER_VC=12258')
print('AUTHORITY_CHANGE=NONE')
print('NEW_RECURRING_ROOT_READS=0')
