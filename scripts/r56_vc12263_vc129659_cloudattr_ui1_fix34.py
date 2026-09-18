from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
reader=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedSnapshotReader.kt'
build=root/'app/build.gradle.kts'

m=main.read_text()
rd=reader.read_text()
b=build.read_text()

assert 'versionCode = 12263' in b
b=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r2-vc12263-vc129659-cloudattr-ui1-fix34"',b,count=1)

m=m.replace('syncModule=="129653"','syncModule=="129659"')
m=m.replace('VC129653 / VC12263','VC129659 / VC12263')
rd=rd.replace("MODULE_VERSION_CODE='129653'","MODULE_VERSION_CODE='129659'")

start=m.index('@Composable fun ThoughtsCard(s:RuntimeState)')
end=m.index('@Composable fun AgentRebuild3Card',start)
block=m[start:end]

old='''    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider=envField(s.brain,"CLOUD_PROVIDER").ifBlank{if(cloudConnection!="UNKNOWN") "GEMINI" else "—"}
    val cloudInControl=envField(s.brain,"CLOUD_IN_CONTROL").ifBlank{if(currentBrain=="GEMINI") "YES" else "NO"}'''
new='''    val cloudState=envField(s.brain,"CLOUD_PLAN_STATE").ifBlank{"UNAVAILABLE"}
    val cloudConnection=envField(s.brain,"CLOUD_CONNECTION_STATUS").ifBlank{"UNKNOWN"}
    val cloudProvider=envField(s.brain,"CLOUD_PROVIDER").ifBlank{if(cloudConnection!="UNKNOWN") "GEMINI" else "—"}
    val cloudControlProvider=envField(s.brain,"CLOUD_CONTROL_PROVIDER").ifBlank{
        when{
            currentBrain=="GEMINI" -> "GEMINI"
            envField(s.brain,"HERMES_BACKEND").equals("CLOUD",true) && (currentBrain=="HERMES_H2"||currentBrain=="HERMES_LOCAL") -> "HERMES_CLOUD"
            else -> "NONE"
        }
    }
    val cloudPlanProvider=envField(s.brain,"CLOUD_PLAN_PROVIDER").ifBlank{
        when{
            cloudControlProvider=="GEMINI" && cloudState!="NOT_USED" && cloudState!="UNAVAILABLE" -> "GEMINI"
            cloudControlProvider=="HERMES_CLOUD" && cloudState!="NOT_USED" && cloudState!="UNAVAILABLE" -> "HERMES_CLOUD"
            else -> "NONE"
        }
    }
    val cloudInControl=when(cloudControlProvider.uppercase()){
        "GEMINI" -> "GEMINI"
        "HERMES_CLOUD","HERMES CLOUD" -> "HERMES CLOUD"
        else -> "NO"
    }
    val cloudPlan=when(cloudPlanProvider.uppercase()){
        "GEMINI" -> "GEMINI"
        "HERMES_CLOUD","HERMES CLOUD" -> "HERMES CLOUD"
        else -> "NOT_USED"
    }'''
assert old in block, 'cloud attribution anchor missing'
block=block.replace(old,new,1)

block=re.sub(
    r'\n    val lang=envField\(s\.thoughts,"LANGUAGE"\).*?\n    val langEngine=envField\(s\.thoughts,"LANGUAGE_ENGINE"\).*?\n',
    '\n',
    block,
    count=1,
)

assert 'Cloud plan: $cloudState' in block
block=block.replace('Cloud plan: $cloudState','Cloud plan: $cloudPlan',1)
assert r'\nLanguage: $lang • $langEngine' in block
block=block.replace(r'\nLanguage: $lang • $langEngine','',1)

m=m[:start]+block+m[end:]

main.write_text(m)
reader.write_text(rd)
build.write_text(b)

M=main.read_text(); RD=reader.read_text(); B=build.read_text()
S=M[M.index('@Composable fun ThoughtsCard(s:RuntimeState)'):M.index('@Composable fun AgentRebuild3Card',M.index('@Composable fun ThoughtsCard(s:RuntimeState)'))]
assert 'versionCode = 12263' in B
assert 'vc12263-vc129659-cloudattr-ui1-fix34' in B
assert 'syncModule=="129659"' in M and 'syncCc=="12263"' in M
assert "MODULE_VERSION_CODE='129659'" in RD and "CONTROL_CENTER_VERSION_CODE='12263'" in RD
assert 'CLOUD_CONTROL_PROVIDER' in S and 'CLOUD_PLAN_PROVIDER' in S
assert 'Cloud in control: $cloudInControl' in S
assert 'Cloud plan: $cloudPlan' in S
assert 'Language: $lang' not in S
assert 'val lang=' not in S and 'val langEngine=' not in S
assert 'Memory:' in S
print('VC12263_VC129659_CLOUDATTR_UI1_FIX34=PASS')
print('PAIR=VC129659+VC12263')
print('LANGUAGE_UI=HIDDEN_ONLY')
print('CLOUD_ATTRIBUTION=PROVIDER_AWARE')
print('LAYOUT_CHANGE=NONE')
