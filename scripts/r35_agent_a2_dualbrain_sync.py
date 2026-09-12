#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12239',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r22-r92ui6-fix2-cog1-hcc1-fullsync-fix4-rc1-agent-a2"',bs,count=1)
b.write_text(bs)

ms=m.read_text()

# R34 authority text -> A2 exact two-brain contract.
old_sync='BoxCard("DJAEGER-AI SYNC","Target module: FIX4 BASELINE RC1 • r92 lineage\\nStrategic path: Gemini-first valid typed policy • Hermes/Local AI fallback\\nHardware path: local typed executor / Root Authority only\\nControl Center path: official typed djaeger-ai commands only",true)'
new_sync='BoxCard("DJAEGER-AI SYNC","Target module: GOLDEN1 RC1 • DUAL-BRAIN AGENT A2\\nCloud brain: GEMINI • Local brain: HERMES H2\\nFinal decision + execution owner: AI AGENT A2\\nHardware path: AI Agent A2 → Root Authority → readback/rollback",true)'
assert old_sync in ms, 'R35_FAIL=sync-anchor'
ms=ms.replace(old_sync,new_sync,1)

old_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / fallback state reported";else->"State published"};val brain=envField(s.brain,"CURRENT_BRAIN").ifBlank{envField(s.brain,"SOURCE")};val strategic=when(brain){"GEMINI"->"GEMINI • VALID TYPED POLICY";"HERMES_LOCAL"->"HERMES LOCAL";else->if(brain.isBlank())"UNPUBLISHED" else "LOCAL AI • $brain"};return "Local brain: ${if(s.brain.isBlank())"not published" else "available"}\\nEnvelope: ${if(s.envelope.isBlank())"not published" else "available"}\\nGemini: $gem\\nStrategic authority: $strategic\\nHardware authority: LOCAL TYPED EXECUTOR"}'
new_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / transport state reported";else->"State published"};val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"};val ast=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"};val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"};return "Cloud brain: GEMINI • $gem\\nLocal brain: HERMES H2\\nAgent: A2 • $ast\\nWinner: $winner • score $score\\nFinal hardware authority: AI AGENT A2 → ROOT AUTHORITY"}'
assert old_summary in ms, 'R35_FAIL=summary-anchor'
ms=ms.replace(old_summary,new_summary,1)

old_monitor='BoxCard("MONITOR INVARIANTS","READ-ONLY application\\nNo direct sysfs writes\\nNo network/game traffic manipulation\\nGemini strategic authority requires a fresh validated typed policy\\nHardware writes remain local typed executor only")'
new_monitor='BoxCard("MONITOR INVARIANTS","READ-ONLY application\\nExactly two brains: Gemini + Hermes H2\\nNo third AI brain\\nAI Agent A2 is final decision/execution owner\\nRoot Authority performs verified hardware transaction\\nNo network/game traffic manipulation")'
assert old_monitor in ms, 'R35_FAIL=safety-anchor'
ms=ms.replace(old_monitor,new_monitor,1)

# Add Agent card directly before Hermes in Overview, preserving requested visual hierarchy.
needle='NetworkCard(s.network);HermesCard(s);HumanComfortHcc1Card(s);ContextVNextCard(s);'
replacement='NetworkCard(s.network);AgentA2Card(s);HermesCard(s);HumanComfortHcc1Card(s);ContextVNextCard(s);'
assert needle in ms, 'R35_FAIL=overview-order-anchor'
ms=ms.replace(needle,replacement,1)

agent_card=r'''
@Composable fun AgentA2Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"A2"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"}
    val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"}
    val reason=envField(s.brain,"AGENT_REASON").ifBlank{"—"}
    val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"GEMINI"}
    val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"HERMES_H2"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"NONE"}
    val direct=envField(s.brain,"DIRECT_ROOT_AUTHORITY").ifBlank{"1"}
    BoxCard("AI AGENT $version • FINAL AUTHORITY","Cloud brain: $cloud\nLocal brain: $local\nThird brain: $third\nState: $state\nWinner: $winner • Score: $score\nReason: $reason\nDecision owner: AI AGENT A2\nExecution owner: AI AGENT A2\nDirect Root Authority: ${if(direct=="1")"YES" else direct}",true)
}
'''
insert_at=ms.index('@Composable fun History(s:RuntimeState)')
ms=ms[:insert_at]+agent_card+'\n'+ms[insert_at:]

# Remove obsolete UI semantics. Hermes is the sole local brain; its memory is internal cognition.
replacements={
    'Validasi Local AI':'Verifikasi Agent',
    'LOCAL AI':'HERMES H2',
    'Local AI':'Hermes H2',
    'LOCAL TYPED EXECUTOR':'AI AGENT A2',
    'local typed executor':'AI Agent A2',
    'Gemini-first':'Gemini + Hermes dual-brain',
}
for a,z in replacements.items(): ms=ms.replace(a,z)

m.write_text(ms)

M=m.read_text(); B=b.read_text()
assert 'versionCode = 12239' in B
assert 'agent-a2' in B
for x in ['AI AGENT A2 • FINAL AUTHORITY','AGENT_WINNER','AGENT_STATE','AGENT_SCORE','AGENT_REASON','BRAIN_CLOUD','BRAIN_LOCAL','THIRD_BRAIN','Exactly two brains: Gemini + Hermes H2','Final hardware authority: AI AGENT A2 → ROOT AUTHORITY']:
    assert x in M, x
for forbidden in ['Validasi Local AI','Local AI','LOCAL AI','LOCAL TYPED EXECUTOR','local typed executor']:
    assert forbidden not in M, forbidden
start=M.index('@Composable fun Overview(s:RuntimeState)'); end=M.index('@Composable fun StatusCard',start); O=M[start:end]
required=['ThoughtsCard(s);','AgentA2Card(s);','HermesCard(s);']
pos=[O.index(x) for x in required]
assert pos==sorted(pos), pos
print('AGENT_A2_UI_SYNC=PASS')
print('EXACT_TWO_BRAINS=PASS')
print('AGENT_A2_AUTHORITY_SEMANTICS=PASS')
print('OVERVIEW_THOUGHT_AGENT_HERMES_ORDER=PASS')
