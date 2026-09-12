#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
b=root/'app/build.gradle.kts'
ms=m.read_text(); bs=b.read_text()

bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12242',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.2-agent-a2-sync1-fix2"',bs,count=1)
ms=ms.replace('CONTROL CENTER • v0.12.2 A2 SYNC1 FIX1 • REALTIME 1s','CONTROL CENTER • v0.12.2 A2 SYNC1 FIX2 • REALTIME 1s')
ms=ms.replace('DJAEGER Control Center v0.12.2 A2 SYNC1 FIX1\\n[','DJAEGER Control Center v0.12.2 A2 SYNC1 FIX2\\n[')

# Remove obsolete third-brain compatibility labels from UI semantics entirely.
start=ms.index('private fun brainLabel(raw:String):String')
end=ms.index('private fun ageLabel',start)
new_brain='''private fun brainLabel(raw:String):String = when(raw){
    "GEMINI"->"GEMINI"
    "HERMES_LOCAL","HERMES_H2"->"HERMES H2"
    "AI_AGENT_A2","AGENT_A2"->"AI AGENT A2"
    else->raw.ifBlank{"—"}
}
'''
ms=ms[:start]+new_brain+ms[end:]

# Agent-centered Thought semantics. Gemini/Hermes reason; Agent owns final choice.
thought_start=ms.index('@Composable fun ThoughtsCard')
thought_end=ms.index('private fun currentRange',thought_start)
th=ms[thought_start:thought_end]
th=th.replace('    val cloudInControl=envField(s.brain,"CLOUD_IN_CONTROL").ifBlank{if(currentBrain=="GEMINI") "YES" else "NO"}\n','    val agentWinner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"}\n')
th=re.sub(r'val thoughtTitle=when\{.*?\n    \}', '''val thoughtTitle=when{
        thoughtSrc=="GEMINI"&&isFresh->"PEMIKIRAN GEMINI"
        thoughtSrc=="GEMINI"->"LAST GEMINI THOUGHT"
        thoughtSrc.contains("HERMES",ignoreCase=true)->"PEMIKIRAN HERMES H2"
        else->"PEMIKIRAN DJAEGER"
    }''', th, count=1, flags=re.S)
th=th.replace('Cloud in control: $cloudInControl','Agent winner: $agentWinner')
th=th.replace('Active brain: ${brainLabel(currentBrain)}','Reasoning source: ${brainLabel(currentBrain)}')
assert 'CLOUD_IN_CONTROL' not in th
assert 'LOCAL_AI' not in th
ms=ms[:thought_start]+th+ms[thought_end:]

# Hermes is the local reasoner only; it never becomes the executor/validator layer.
hermes_start=ms.index('@Composable fun HermesCard')
hermes_end=ms.index('@Composable fun HumanComfortHcc1Card',hermes_start)
h=ms[hermes_start:hermes_end]
h=h.replace('    val currentBrain=envField(s.brain,"CURRENT_BRAIN")\n    val finalSource=envField(s.brain,"FINAL_SOURCE")\n','    val currentBrain=envField(s.brain,"CURRENT_BRAIN")\n    val finalSource=envField(s.brain,"FINAL_SOURCE")\n    val agentWinner=envField(s.brain,"AGENT_WINNER").ifBlank{"NONE"}\n')
state_start=h.index('    val displayState=when(hState){')
state_end=h.index('    val body=',state_start)
new_state='''    val displayState=when(hState){
        "VALID"->if(agentWinner=="HERMES") "SELECTED BY AGENT" else "READY"
        "LOW_CONFIDENCE"->"LEARNING • LOW CONFIDENCE"
        "UNAVAILABLE"->"UNAVAILABLE"
        else->hState
    }
    val authority="REASONING ONLY • AI AGENT A2 OWNS DECISION + EXECUTION"
'''
h=h[:state_start]+new_state+h[state_end:]
ms=ms[:hermes_start]+h+ms[hermes_end:]

# Strategy fallback text must describe Agent internal verification, not a removed Local validator.
ms=ms.replace('else "LOCAL VALIDATOR / FAIL-CLOSED"','else "AGENT A2 INTERNAL VERIFICATION / FAIL-CLOSED"')

# Broken vault SELECT: SAVE_KEY was never handled by bridgeOp. Route to the real SAVE handler.
ms=ms.replace('keyInput=k; bridgeOp="SAVE_KEY"','keyInput=k; bridgeOp="SAVE"')

# Make diagnostic button results visible. The old state variables were updated but never rendered.
diag_anchor='''        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="RECOVERY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RECOVERY")}
            Button(onClick={bridgeOp="SNAPSHOT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SNAPSHOT")}
        }
'''
assert diag_anchor in ms,'R38_FAIL=diagnostic-buttons-anchor'
diag_cards=diag_anchor+'''        BoxCard("DIAGNOSTIC COMMAND RESULTS","AUTHORITY SYNC\\n$authorityStatus\\n\\nKERNEL CAPABILITY\\n$kernelStatus\\n\\nMATURITY AUDIT\\n$auditStatus\\n\\nSESSION RECOVERY\\n$recoveryStatus\\n\\nSNAPSHOT LIFECYCLE\\n$snapshotStatus",true)
'''
ms=ms.replace(diag_anchor,diag_cards,1)

# Correct misleading labels and Safety semantics.
ms=ms.replace('BoxCard("GEMINI INTELLIGENCE HUMAN VIEW",retained,true)','BoxCard("DJAEGER CURRENT INTERPRETATION",retained,true)')
ms=ms.replace('''BoxCard("MONITOR INVARIANTS","READ-ONLY application\\nExactly two brains: Gemini + Hermes H2\\nNo third AI brain\\nAI Agent A2 is final decision/execution owner\\nRoot Authority performs verified hardware transaction\\nNo network/game traffic manipulation")''','''BoxCard("MONITOR INVARIANTS","No direct hardware writes from Control Center\\nControls use typed djaeger-ai interfaces only\\nExactly two brains: Gemini + Hermes H2\\nNo third AI brain\\nAI Agent A2 is final decision/execution owner\\nRoot Authority performs verified hardware transaction\\nNo network/game traffic manipulation")''')
ms=ms.replace('Control Center does not alter CPU/GPU state. Original-state restoration is owned by DJAEGER Root Authority','Control Center does not write CPU/GPU nodes directly. Typed requests are executed by AI Agent A2 / Root Authority. Original-state restoration is owned by DJAEGER Root Authority')

# Matched-pair display identity and stale CI marker.
ms=ms.replace('Control Center: v0.12.2 • Agent A2 SYNC1','Control Center: v0.12.2 • Agent A2 SYNC1 FIX2')
ms=ms.replace('// CI_BASELINE_MARKER: v0.10.1 RC • HUD STABLE + AI/KERNEL SYNC','// CI_BASELINE_MARKER: v0.12.2 • AGENT A2 SYNC1 FIX2')

m.write_text(ms); b.write_text(bs)
M=m.read_text(); B=b.read_text()
assert 'versionCode = 12242' in B
assert 'versionName = "0.12.2-agent-a2-sync1-fix2"' in B
for token in ['Agent winner: $agentWinner','REASONING ONLY • AI AGENT A2 OWNS DECISION + EXECUTION','AGENT A2 INTERNAL VERIFICATION / FAIL-CLOSED','bridgeOp="SAVE"','DIAGNOSTIC COMMAND RESULTS','DJAEGER CURRENT INTERPRETATION','No direct hardware writes from Control Center','AGENT A2 SYNC1 FIX2']:
    assert token in M,token
for stale in ['LOCAL_AI','LOCAL_LEARNED','LOCAL_BASELINE','LOCAL VALIDATOR/TYPED EXECUTOR','STANDBY_GEMINI_ONLINE','READ-ONLY application','GEMINI INTELLIGENCE HUMAN VIEW','bridgeOp="SAVE_KEY"']:
    assert stale not in M,stale
# Core A2 invariants survive FIX2.
for token in ['THIRD_BRAIN','AI AGENT A2 • FINAL AUTHORITY','HERMES H2 • LOCAL BRAIN','DUALBRAIN-AGENT-A2-SYNC1','MatchedPairSyncCard(s)','sampleSessionKey','runtimeStateStale(s)']:
    assert token in M,token
print('R38_REMOVE_LEGACY_LOCAL_AI_UI=PASS')
print('R38_AGENT_CENTERED_THOUGHTS=PASS')
print('R38_HERMES_REASONER_ONLY=PASS')
print('R38_VAULT_SELECT_HANDLER=PASS')
print('R38_DIAGNOSTIC_RESULTS_VISIBLE=PASS')
print('R38_SAFETY_SEMANTICS=PASS')
