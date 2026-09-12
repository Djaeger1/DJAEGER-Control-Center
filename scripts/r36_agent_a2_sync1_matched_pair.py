#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12240',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.2-agent-a2-sync1"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
old_sync='BoxCard("DJAEGER-AI SYNC","Target module: GOLDEN1 RC1 • DUAL-BRAIN AGENT A2\\nCloud brain: GEMINI • Local brain: HERMES H2\\nFinal decision + execution owner: AI AGENT A2\\nHardware path: AI Agent A2 → Root Authority → readback/rollback",true)'
assert old_sync in ms, 'R36_FAIL=sync-card-anchor'
ms=ms.replace(old_sync,'MatchedPairSyncCard(s)',1)

old_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / transport state reported";else->"State published"};val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"};val ast=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"};val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"};return "Cloud brain: GEMINI • $gem\\nLocal brain: HERMES H2\\nAgent: A2 • $ast\\nWinner: $winner • score $score\\nFinal hardware authority: AI AGENT A2 → ROOT AUTHORITY"}'
new_summary='private fun aiSummary(s:RuntimeState):String{val h=s.geminiHttp.lowercase();val server=s.geminiServer.lowercase();val gem=when{h.isBlank()&&server.isBlank()->"No published Gemini state";"backoff" in server||"error" in h||"fail" in h->"Attention / transport state reported";else->"State published"};val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"UNPUBLISHED"};val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"UNPUBLISHED"};val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"};val ast=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"};val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"};val sync=envField(s.brain,"CONTROL_CENTER_SYNC").ifBlank{"UNPUBLISHED"};return "Cloud brain: $cloud • $gem\\nLocal brain: $local\\nAgent: A2 • $ast\\nWinner: $winner • score $score\\nSync: $sync\\nFinal hardware authority: AI AGENT A2 → ROOT AUTHORITY"}'
assert old_summary in ms, 'R36_FAIL=summary-anchor'
ms=ms.replace(old_summary,new_summary,1)

start=ms.index('@Composable fun AgentA2Card')
end=ms.index('@Composable fun History(s:RuntimeState)',start)
new_cards=r'''@Composable fun MatchedPairSyncCard(s:RuntimeState){
    val expected="DUALBRAIN-AGENT-A2-SYNC1"
    val matched=s.moduleVersion.contains(expected)
    val state=if(matched)"MATCHED" else "MODULE UPDATE REQUIRED"
    BoxCard("DJAEGER-AI MATCHED PAIR","Control Center: v0.12.2 • Agent A2 SYNC1\nModule: ${s.moduleVersion}\nCompatibility: $state\nExpected marker: $expected\nCloud brain: GEMINI\nLocal brain: HERMES H2\nFinal owner: AI AGENT A2",true)
}

@Composable fun AgentA2Card(s:RuntimeState){
    val version=envField(s.brain,"AGENT_VERSION").ifBlank{"UNPUBLISHED"}
    val arch=envField(s.brain,"AGENT_ARCH").ifBlank{"UNPUBLISHED"}
    val state=envField(s.brain,"AGENT_STATE").ifBlank{"UNPUBLISHED"}
    val winner=envField(s.brain,"AGENT_WINNER").ifBlank{"UNPUBLISHED"}
    val score=envField(s.brain,"AGENT_SCORE").ifBlank{"0"}
    val reason=envField(s.brain,"AGENT_REASON").ifBlank{"—"}
    val cloud=envField(s.brain,"BRAIN_CLOUD").ifBlank{"UNPUBLISHED"}
    val local=envField(s.brain,"BRAIN_LOCAL").ifBlank{"UNPUBLISHED"}
    val third=envField(s.brain,"THIRD_BRAIN").ifBlank{"UNPUBLISHED"}
    val direct=envField(s.brain,"DIRECT_ROOT_AUTHORITY").ifBlank{"UNPUBLISHED"}
    val readback=envField(s.brain,"READBACK_REQUIRED").ifBlank{"UNPUBLISHED"}
    val rollback=envField(s.brain,"ROLLBACK_REQUIRED").ifBlank{"UNPUBLISHED"}
    val nativeRole=envField(s.brain,"NATIVE_BASELINE_ROLE").ifBlank{"UNPUBLISHED"}
    val sync=envField(s.brain,"CONTROL_CENTER_SYNC").ifBlank{"UNPUBLISHED"}
    fun yn(v:String)=when(v){"1"->"YES";"0"->"NO";else->v}
    BoxCard("AI AGENT A2 • FINAL AUTHORITY","Version: $version • Architecture: $arch\nCloud brain: $cloud\nLocal brain: $local\nThird brain: $third\nState: $state\nWinner: $winner • Score: $score\nReason: $reason\nDecision owner: AI AGENT A2\nExecution owner: AI AGENT A2\nDirect Root Authority: ${yn(direct)}\nReadback required: ${yn(readback)}\nRollback required: ${yn(rollback)}\nNative baseline: $nativeRole\nContract sync: $sync",true)
}

'''
ms=ms[:start]+new_cards+ms[end:]

m.write_text(ms)
M=m.read_text(); B=b.read_text()
assert 'versionCode = 12240' in B
assert 'versionName = "0.12.2-agent-a2-sync1"' in B
for x in ['DJAEGER-AI MATCHED PAIR','DUALBRAIN-AGENT-A2-SYNC1','s.moduleVersion.contains(expected)','READBACK_REQUIRED','ROLLBACK_REQUIRED','NATIVE_BASELINE_ROLE','CONTROL_CENTER_SYNC','AGENT_ARCH','AI AGENT A2 • FINAL AUTHORITY']:
    assert x in M, x
for forbidden in ['Validasi Local AI','Local AI','LOCAL AI','LOCAL TYPED EXECUTOR','local typed executor']:
    assert forbidden not in M, forbidden
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('@Composable fun StatusCard',M.index('@Composable fun Overview(s:RuntimeState)'))]
assert 'ThoughtsCard(s);AgentA2Card(s);HermesCard(s);' in ov
assert 'MatchedPairSyncCard(s)' in M
print('AGENT_A2_SYNC1_MATCHED_PAIR_UI=PASS')
print('AGENT_A2_SYNC1_RUNTIME_CONTRACT_FIELDS=PASS')
print('AGENT_A2_SYNC1_VERSION_COMPATIBILITY_GATE=PASS')
print('AGENT_A2_SYNC1_EXACT_TWO_BRAINS=PASS')
