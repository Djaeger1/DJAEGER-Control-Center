from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); b=build.read_text()

# SHAREDINT1 is additive to validated GAMEREG1. Pair identity is deliberately bumped
# so an older module/APK cannot be reported as an exact match.
assert 'versionCode = 12258' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1"' in b
b=b.replace('versionCode = 12258','versionCode = 12259',1)
b=b.replace('versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1"','versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1"',1)

old_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1'
assert old_header in m
m=m.replace(old_header,old_header+' • SHAREDINT1',1)

old_vars='''    val syncKernel=envField(s.controlCenterSync,"HERMES_KERNEL")\n    val syncSysfs=envField(s.controlCenterSync,"AGENT_SYSFS")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1"&&syncModule=="129631"&&syncCc=="12258"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)\n'''
new_vars='''    val syncKernel=envField(s.controlCenterSync,"HERMES_KERNEL")\n    val syncSysfs=envField(s.controlCenterSync,"AGENT_SYSFS")\n    val syncGameRegistry=envField(s.controlCenterSync,"GAME_REGISTRY")\n    val syncShared=envField(s.controlCenterSync,"SHARED_INTELLIGENCE")\n    val geminiScope=envField(s.controlCenterSync,"GEMINI_INTELLIGENCE_SCOPE")\n    val hermesScope=envField(s.controlCenterSync,"HERMES_INTELLIGENCE_SCOPE")\n    val geminiReasoningLimit=envField(s.controlCenterSync,"GEMINI_REASONING_LIMIT")\n    val hermesTeacherLoop=envField(s.controlCenterSync,"HERMES_TEACHER_LOOP")\n    val exactMatched=syncContract=="REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1"&&syncModule=="129632"&&syncCc=="12259"&&syncKernel=="KERNEL1"&&syncSysfs=="SYSFS1"&&syncGameRegistry=="GAMEREG1"&&syncShared=="SHAREDINT1"&&geminiScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"&&hermesScope=="DJAEGER_FULL_AVAILABLE_INTELLIGENCE"\n    val identityMatched=s.moduleVersion.contains("REBUILD3",true)&&s.moduleVersion.contains("HK1",true)&&s.moduleVersion.contains("SYSFS1",true)&&s.moduleVersion.contains("CCSYNC1",true)&&s.moduleVersion.contains("GAMEREG1",true)&&s.moduleVersion.contains("SHAREDINT1",true)\n'''
assert old_vars in m
m=m.replace(old_vars,new_vars,1)

old_body='''Decision priority: $priority\\nGemini feed: COMPACT • DELTA / EVENT DRIVEN\\nHermes feed: RICH • LOCAL\\nThird brain: $third'''
new_body='''Decision priority: $priority\\nShared intelligence: ${syncShared.ifBlank{"UNPUBLISHED"}}\\nGemini intelligence: ${geminiScope.ifBlank{"UNPUBLISHED"}}\\nHermes intelligence: ${hermesScope.ifBlank{"UNPUBLISHED"}}\\nGemini reasoning limit from Hermes feature set: ${geminiReasoningLimit.ifBlank{"UNPUBLISHED"}}\\nHermes teacher loop: ${hermesTeacherLoop.ifBlank{"UNPUBLISHED"}}\\nImmediate Gemini facts: DELTA / EVENT DRIVEN\\nThird brain: $third'''
assert old_body in m
m=m.replace(old_body,new_body,1)

main.write_text(m); build.write_text(b)

M=main.read_text(); B=build.read_text()
assert 'versionCode = 12259' in B
assert 'loopfix1-gamereg1-sharedint1' in B
assert 'GAMEREG1 • SHAREDINT1' in M
assert 'REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1' in M
assert 'syncModule=="129632"&&syncCc=="12259"' in M
assert 'syncGameRegistry=="GAMEREG1"&&syncShared=="SHAREDINT1"' in M
assert 'DJAEGER_FULL_AVAILABLE_INTELLIGENCE' in M
assert 'Gemini reasoning limit from Hermes feature set' in M
assert 'Hermes teacher loop' in M
print('SHAREDINT1_CC_PATCH=PASS')
print('MODULE_VC=129632')
print('CONTROL_CENTER_VC=12259')
print('EXACT_PAIR_CONTRACT=PASS')
