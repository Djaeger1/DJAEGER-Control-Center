#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

# HCC1 FULLSYNC is additive on top of proven UI6 FIX2 + COG1 + OverviewOrder.
bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12234',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync"',bs,count=1)
b.write_text(bs)

# 1) Map HCC1 as a first-class cc_snapshot section. No new recurring root read.
cs=mapper.read_text()
field_anchor='        val hermesResearchV2: String,\n'
assert field_anchor in cs, 'HCC1_UI_FAIL=mapper-field-anchor'
if 'val hermesHumanComfort: String,' not in cs:
    cs=cs.replace(field_anchor,field_anchor+'        val hermesHumanComfort: String,\n',1)
map_anchor='            hermesResearchV2 = s["HERMES_RESEARCH_V2"].orEmpty(),\n'
assert map_anchor in cs, 'HCC1_UI_FAIL=mapper-map-anchor'
if 'hermesHumanComfort = s["HERMES_HUMAN_COMFORT"].orEmpty(),' not in cs:
    cs=cs.replace(map_anchor,map_anchor+'            hermesHumanComfort = s["HERMES_HUMAN_COMFORT"].orEmpty(),\n',1)
mapper.write_text(cs)

# 2) Carry mapped HCC1 truth into RuntimeState.
rs=r.read_text()
state_anchor='val hermesResearchV2:String=""'
assert state_anchor in rs, 'HCC1_UI_FAIL=runtime-state-anchor'
if 'val hermesHumanComfort:String=""' not in rs:
    rs=rs.replace(state_anchor,state_anchor+',val hermesHumanComfort:String=""',1)
repo_anchor='hermesResearchV2=mapped.hermesResearchV2,'
assert repo_anchor in rs, 'HCC1_UI_FAIL=repository-map-anchor'
if 'hermesHumanComfort=mapped.hermesHumanComfort,' not in rs:
    rs=rs.replace(repo_anchor,repo_anchor+'hermesHumanComfort=mapped.hermesHumanComfort,',1)

# 3) Typed HCC1 control methods. Fixed allowlists only; no arbitrary shell text.
method_anchor='    private fun suStdin(command:String,input:String,timeoutMs:Long=30000):Pair<Int,String>{'
assert method_anchor in rs, 'HCC1_UI_FAIL=control-method-anchor'
if 'suspend fun setHumanComfortPreset' not in rs:
    methods=r'''    suspend fun setHumanComfortPreset(preset:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val arg=when(preset.uppercase()){
            "COOL_STABLE"->"cool-stable"
            "BASELINE"->"baseline"
            "RESET"->"reset"
            else->return@withContext Pair(false,"INVALID_COMFORT_PRESET")
        }
        val (rc,out)=su("djaeger-ai comfort $arg",5000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"COMFORT_REQUEST_SENT" else "COMFORT_COMMAND_FAILED"})
    }

    suspend fun submitHumanComfortFeedback(level:String):Pair<Boolean,String> = withContext(Dispatchers.IO){
        val arg=when(level.uppercase()){
            "VERY_COMFORTABLE"->"very-comfortable"
            "COMFORTABLE"->"comfortable"
            "LESS_COMFORTABLE"->"less-comfortable"
            "UNCOMFORTABLE"->"uncomfortable"
            else->return@withContext Pair(false,"INVALID_COMFORT_FEEDBACK")
        }
        val (rc,out)=su("djaeger-ai feedback $arg",5000)
        Pair(rc==0,out.trim().ifBlank{if(rc==0)"COMFORT_FEEDBACK_RECORDED" else "COMFORT_FEEDBACK_FAILED"})
    }

'''
    rs=rs.replace(method_anchor,methods+method_anchor,1)

# Prove recurring snapshot still uses only ConsolidatedSnapshotReader.
start=rs.index('    suspend fun snapshot():RuntimeState=withContext(Dispatchers.IO){')
end=rs.index('    suspend fun setUserMode',start)
snap=rs[start:end]
for required in ['ConsolidatedSnapshotReader','hermesHumanComfort=mapped.hermesHumanComfort']:
    assert required in snap, 'HCC1_UI_FAIL=snapshot-'+required
for forbidden in ['/sys/','human_comfort_runtime.conf','human_comfort_memory.tsv','djaeger-ai comfort','djaeger-ai feedback','ProcessBuilder']:
    assert forbidden not in snap, 'HCC1_UI_FAIL=extra-recurring-read-'+forbidden
r.write_text(rs)

# 4) UI6 first-class HCC1 card + typed controls.
ms=m.read_text()
old_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-overvieworder • HERMES COGNITION VNEXT'
new_header='CONTROL CENTER • v0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync • HERMES COGNITION VNEXT • HCC1'
assert old_header in ms, 'HCC1_UI_FAIL=header-anchor'
ms=ms.replace(old_header,new_header,1)

card_anchor='@Composable fun ContextVNextCard(s:RuntimeState)'
assert card_anchor in ms, 'HCC1_UI_FAIL=context-card-anchor'
if '@Composable fun HumanComfortHcc1Card(s:RuntimeState)' not in ms:
    card=r'''@Composable fun HumanComfortHcc1Card(s:RuntimeState){
    val body=s.hermesHumanComfort.trim().ifBlank{"UNAVAILABLE — HCC1 human comfort state not published by module."}
    BoxCard("HERMES • HUMAN COMFORT HCC1",body,true)
}

'''
    ms=ms.replace(card_anchor,card+card_anchor,1)

# Keep the user's exact telemetry placement; HCC1 sits immediately after Hermes H2.
ov_start=ms.index('@Composable fun Overview(s:RuntimeState)')
ov_end=ms.index('@Composable fun StatusCard',ov_start)
ov=ms[ov_start:ov_end]
anchor='HermesCard(s);ContextVNextCard(s);'
assert anchor in ov, 'HCC1_UI_FAIL=overview-hermes-context-anchor'
ov=ov.replace(anchor,'HermesCard(s);HumanComfortHcc1Card(s);ContextVNextCard(s);',1)
ms=ms[:ov_start]+ov+ms[ov_end:]

# Add HCC1 control result state to AI tab.
status_anchor='    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}\n'
assert status_anchor in ms, 'HCC1_UI_FAIL=ai-status-anchor'
if 'comfortCommandStatus' not in ms:
    ms=ms.replace(status_anchor,status_anchor+'    var comfortCommandStatus by remember{mutableStateOf("HCC1 controls ready. Current truth is read from cc_snapshot.")}\n',1)

# Extend the existing typed bridge operation dispatcher.
case_anchor='            "SNAPSHOT"->{val r=repo.snapshotLifecycleStatus();snapshotStatus=r.second.ifBlank{"SNAPSHOT_STATUS=EMPTY"}}\n'
assert case_anchor in ms, 'HCC1_UI_FAIL=ai-operation-anchor'
if '"COMFORT_COOL"' not in ms:
    cases='''            "COMFORT_COOL"->{val r=repo.setHumanComfortPreset("COOL_STABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}\n            "COMFORT_BASELINE"->{val r=repo.setHumanComfortPreset("BASELINE");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}\n            "COMFORT_RESET"->{val r=repo.setHumanComfortPreset("RESET");comfortCommandStatus=r.second.ifBlank{"COMFORT_PRESET_EMPTY"}}\n            "FEEDBACK_VERY_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("VERY_COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}\n            "FEEDBACK_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}\n            "FEEDBACK_LESS_COMFORTABLE"->{val r=repo.submitHumanComfortFeedback("LESS_COMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}\n            "FEEDBACK_UNCOMFORTABLE"->{val r=repo.submitHumanComfortFeedback("UNCOMFORTABLE");comfortCommandStatus=r.second.ifBlank{"COMFORT_FEEDBACK_EMPTY"}}\n'''
    ms=ms.replace(case_anchor,case_anchor+cases,1)

# Put controls directly after existing mode authority, keeping AI layout family intact.
mode_anchor='        BoxCard("MODE AUTHORITY","Mode changes use only the trusted djaeger-ai mode interface. Native thermal protection remains independent and authoritative.",true)\n'
assert mode_anchor in ms, 'HCC1_UI_FAIL=mode-authority-anchor'
if 'HUMAN COMFORT HCC1 CONTROL' not in ms:
    controls=r'''        BoxCard("HUMAN COMFORT HCC1 CONTROL",s.hermesHumanComfort.trim().ifBlank{"HCC1 state waiting for module publication."}+"\n\nLast command: $comfortCommandStatus",true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="COMFORT_COOL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("COOL STABLE",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="COMFORT_BASELINE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("BASELINE",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="COMFORT_RESET"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RESET",style=MaterialTheme.typography.labelSmall)}
        }
        Text("FEEDBACK KENYAMANAN • menjadi evidence personal HCC1",color=Muted,style=MaterialTheme.typography.labelMedium)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            OutlinedButton(onClick={bridgeOp="FEEDBACK_VERY_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SANGAT NYAMAN",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="FEEDBACK_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("NYAMAN",style=MaterialTheme.typography.labelSmall)}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            OutlinedButton(onClick={bridgeOp="FEEDBACK_LESS_COMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KURANG NYAMAN",style=MaterialTheme.typography.labelSmall)}
            OutlinedButton(onClick={bridgeOp="FEEDBACK_UNCOMFORTABLE"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("TIDAK NYAMAN",style=MaterialTheme.typography.labelSmall)}
        }
'''
    ms=ms.replace(mode_anchor,mode_anchor+controls,1)

# Final exact ordering and safety gates.
ov_start=ms.index('@Composable fun Overview(s:RuntimeState)'); ov_end=ms.index('@Composable fun StatusCard',ov_start); ov=ms[ov_start:ov_end]
for required in ['ThoughtsCard(s);','Metric("FPS"','Metric("Frame"','Metric("Jank"','ThermalRow(s);','NetworkCard(s.network);','HermesCard(s);','HumanComfortHcc1Card(s);','ContextVNextCard(s);']:
    assert required in ov, 'HCC1_UI_FAIL=overview-'+required
idx=[ov.index(x) for x in ['ThoughtsCard(s);','Metric("FPS"','Metric("Frame"','Metric("Jank"','ThermalRow(s);','NetworkCard(s.network);','HermesCard(s);','HumanComfortHcc1Card(s);','ContextVNextCard(s);']]
assert idx==sorted(idx), 'HCC1_UI_FAIL=overview-order'
for required in ['HUMAN COMFORT HCC1 CONTROL','COOL STABLE','BASELINE','RESET','SANGAT NYAMAN','NYAMAN','KURANG NYAMAN','TIDAK NYAMAN']:
    assert required in ms, 'HCC1_UI_FAIL=missing-control-'+required
for forbidden in ['iptables','ip6tables','settings put','setprop','force-stop','/sys/class/','djaeger-root-authority']:
    assert forbidden not in card, 'HCC1_UI_FAIL=card-authority-'+forbidden
m.write_text(ms)

# Cross-layer full-sync proof.
cs=mapper.read_text(); rs=r.read_text(); ms=m.read_text()
assert 's["HERMES_HUMAN_COMFORT"]' in cs
assert 'hermesHumanComfort=mapped.hermesHumanComfort' in rs
assert 'djaeger-ai comfort $arg' in rs
assert 'djaeger-ai feedback $arg' in rs
print('HCC1_UI_BASELINE=UI6_FIX2_COG1_OVERVIEWORDER')
print('HCC1_FIRST_CLASS_SECTION=HERMES_HUMAN_COMFORT')
print('HCC1_MODULE_TO_MAPPER=PASS')
print('HCC1_MAPPER_TO_RUNTIME_STATE=PASS')
print('HCC1_OVERVIEW_CARD=PASS')
print('HCC1_PRESET_CONTROL=COOL_STABLE+BASELINE+RESET')
print('HCC1_FEEDBACK_CONTROL=VERY_COMFORTABLE+COMFORTABLE+LESS_COMFORTABLE+UNCOMFORTABLE')
print('HCC1_CONTROL_PATH=TYPED_DJAEGER_AI_ONLY')
print('HCC1_EXTRA_RECURRING_ROOT_READS=0')
print('HCC1_HARDWARE_AUTHORITY_CHANGE=NONE')
print('HCC1_NETWORK_GAME_TRAFFIC_CHANGE=NONE')
