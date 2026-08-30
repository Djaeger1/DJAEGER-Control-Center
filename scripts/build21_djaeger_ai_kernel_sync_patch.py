from pathlib import Path
import re

# DJAEGER Control Center Build 21
pkg = Path('app/src/main/java/com/djaeger/controlcenter')

# Normalize version metadata regardless of which earlier patch string survived.
g = Path('app/build.gradle.kts')
s = g.read_text()
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 22', s, count=1)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.10.0-rc-ai-kernel-sync"', s, count=1)
g.write_text(s)

# Root bridge additions: all control remains routed through djaeger-ai.
r = pkg / 'DjaegerRepository.kt'
s = r.read_text()
anchor = '\n    private fun parseTelemetry'
extra = '''
    suspend fun authoritySyncStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai authority-sync status"); Pair(rc==0,out.trim())
    }
    suspend fun kernelCapabilitySummary():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai kernel-capability-summary"); Pair(rc==0,out.trim())
    }
    suspend fun maturityAudit():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai maturity-audit"); Pair(rc==0,out.trim())
    }
    suspend fun recoveryStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai session-recovery-status"); Pair(rc==0,out.trim())
    }
    suspend fun snapshotLifecycleStatus():Pair<Boolean,String> = withContext(Dispatchers.IO){
        val (rc,out)=su("djaeger-ai snapshot-lifecycle-status"); Pair(rc==0,out.trim())
    }
'''
if 'suspend fun authoritySyncStatus()' not in s:
    if anchor not in s: raise SystemExit('DjaegerRepository parseTelemetry anchor not found')
    s = s.replace(anchor, extra + anchor, 1)
r.write_text(s)

m = pkg / 'MainActivity.kt'
s = m.read_text()
# Normalize any historical cockpit subtitle to the current build.
s = re.sub(r'GAMING TURBO\s*•\s*v[0-9.]+\s*RC\s*•[^"\n]*', 'GAMING TURBO • v0.10.0 RC • DJAEGER AI + KERNEL SYNC • REALTIME 1s', s, count=1)
s = re.sub(r'DJAEGER v0\.[0-9.]+ RC', 'DJAEGER v0.10.0 RC', s)

state_anchor = 'var knowledgeStatus by remember{mutableStateOf("Knowledge status not loaded yet.")}'
state_extra = '''var knowledgeStatus by remember{mutableStateOf("Knowledge status not loaded yet.")}
    var authorityStatus by remember{mutableStateOf("Authority sync not loaded yet.")}
    var kernelStatus by remember{mutableStateOf("Kernel capability not loaded yet.")}
    var auditStatus by remember{mutableStateOf("Maturity audit not run yet.")}
    var recoveryStatus by remember{mutableStateOf("Recovery state not loaded yet.")}
    var snapshotStatus by remember{mutableStateOf("Snapshot lifecycle not loaded yet.")}'''
if state_anchor in s:
    s = s.replace(state_anchor, state_extra, 1)

switch_anchor = '''            "KNOWLEDGE"->{val r=repo.geminiKnowledgeStatus();knowledgeStatus=r.second.ifBlank{"KNOWLEDGE_STATUS=EMPTY"}}
            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}'''
switch_extra = '''            "KNOWLEDGE"->{val r=repo.geminiKnowledgeStatus();knowledgeStatus=r.second.ifBlank{"KNOWLEDGE_STATUS=EMPTY"}}
            "CLEAR_CHAT"->{val r=repo.geminiChatClear();chatResult=r.second.ifBlank{"CHAT_HISTORY_CLEARED"}}
            "AUTHORITY"->{val r=repo.authoritySyncStatus();authorityStatus=r.second.ifBlank{"AUTHORITY_SYNC=EMPTY"}}
            "KERNEL"->{val r=repo.kernelCapabilitySummary();kernelStatus=r.second.ifBlank{"KERNEL_CAPABILITY=EMPTY"}}
            "AUDIT"->{val r=repo.maturityAudit();auditStatus=r.second.ifBlank{"MATURITY_AUDIT=EMPTY"}}
            "RECOVERY"->{val r=repo.recoveryStatus();recoveryStatus=r.second.ifBlank{"RECOVERY_STATUS=EMPTY"}}
            "SNAPSHOT"->{val r=repo.snapshotLifecycleStatus();snapshotStatus=r.second.ifBlank{"SNAPSHOT_STATUS=EMPTY"}}'''
if switch_anchor in s:
    s = s.replace(switch_anchor, switch_extra, 1)

knowledge_card = 'BoxCard("GEMINI KNOWLEDGE + EVOLUTION",knowledgeStatus,true)'
new_cards = '''BoxCard("GEMINI KNOWLEDGE + EVOLUTION",knowledgeStatus,true)
        BoxCard("DJAEGER AI ↔ KERNEL AUTHORITY SYNC",authorityStatus,true)
        BoxCard("LIVE KERNEL CAPABILITY",kernelStatus,true)
        BoxCard("SESSION RECOVERY",recoveryStatus,true)
        BoxCard("SESSION SNAPSHOT LIFECYCLE",snapshotStatus,true)
        BoxCard("MATURITY / REGRESSION AUDIT",auditStatus,true)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="AUTHORITY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SYNC")}
            Button(onClick={bridgeOp="KERNEL"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("KERNEL")}
            Button(onClick={bridgeOp="AUDIT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("AUDIT")}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(6.dp)){
            Button(onClick={bridgeOp="RECOVERY"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("RECOVERY")}
            Button(onClick={bridgeOp="SNAPSHOT"},enabled=bridgeOp==null,modifier=Modifier.weight(1f)){Text("SNAPSHOT")}
        }'''
if knowledge_card in s:
    s = s.replace(knowledge_card, new_cards, 1)

s = s.replace('val supported=s.moduleVersion.contains("12.9.");', 'val supported=s.moduleVersion.contains("12.9.") || s.moduleVersion.contains("13.");')
s = s.replace('BoxCard("GEMINI CONVERSATION",chatResult,true)', 'BoxCard("GEMINI CONVERSATION",chatResult+"\\n\\nTransport errors affect Gemini chat only; Local AI/kernel execution remains independently observable below.",true)')
m.write_text(s)

h = pkg / 'DjaegerHudService.kt'
s = h.read_text()
s = s.replace('◆  DJAEGER GAME TURBO', '◆  DJAEGER AI GAME TURBO')
s = s.replace('DJAEGER Game Turbo', 'DJAEGER AI Game Turbo')
h.write_text(s)

print('Build 21 patch applied')
