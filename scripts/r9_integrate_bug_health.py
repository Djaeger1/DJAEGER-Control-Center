#!/usr/bin/env python3
from pathlib import Path
import re

repo=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt')
r=repo.read_text()
# r7 adds NetworkState to RuntimeState, so anchor on the data-class declaration
# instead of an exact pre-r7 string. This preserves all established fields.
if 'val bugHealth:BugHealthState=BugHealthState()' not in r:
    m=re.search(r'^data class RuntimeState\((.*)\)$', r, re.MULTILINE)
    if not m:
        raise SystemExit('R9_BUG_UI_FAIL=RuntimeState-anchor')
    declaration=m.group(0)
    patched=declaration[:-1]+',val bugHealth:BugHealthState=BugHealthState())'
    r=r[:m.start()]+patched+r[m.end():]

# The r9 cutover intentionally keeps NetworkState as the final named argument.
# Insert BugHealth next to the mapped snapshot fields without depending on
# argument order, so network preservation and BugHealth integration coexist.
if 'bugHealth=mapped.bugHealth' not in r:
    anchor='            network=network\n'
    if anchor not in r:
        raise SystemExit('R9_BUG_UI_FAIL=cutover-network-anchor')
    r=r.replace(anchor,'            network=network,\n            bugHealth=mapped.bugHealth\n',1)
repo.write_text(r)

p=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
s=p.read_text()
if 'import android.Manifest' not in s:
    s=s.replace('import android.os.Bundle\n','import android.os.Bundle\nimport android.Manifest\nimport android.os.Build\n')

old='@Composable fun App(){val repo=remember{DjaegerRepository()};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()}'
new='@Composable fun App(){val repo=remember{DjaegerRepository()};val context=androidx.compose.ui.platform.LocalContext.current;val notifier=remember{BugNotifier(context)};var state by remember{mutableStateOf(RuntimeState())};var tab by remember{mutableIntStateOf(0)};val samples=remember{mutableStateListOf<Sample>()}'
if old not in s: raise SystemExit('R9_BUG_UI_FAIL=App-anchor')
s=s.replace(old,new,1)

old_loop='state=repo.snapshot();if(state.root&&state.installed&&state.sampleFresh)'
new_loop='state=repo.snapshot();notifier.notifyIfNeeded(state.bugHealth);if(state.root&&state.installed&&state.sampleFresh)'
if old_loop not in s: raise SystemExit('R9_BUG_UI_FAIL=poll-anchor')
s=s.replace(old_loop,new_loop,1)

old_tabs='listOf("Overview","Session","Charts","AI","History","Safety","Logs")'
new_tabs='listOf("Overview","Session","Charts","AI","History","Safety","Bug & Health","Logs")'
if old_tabs not in s: raise SystemExit('R9_BUG_UI_FAIL=tabs-anchor')
s=s.replace(old_tabs,new_tabs,1)
old_when='when(tab){0->Overview(state);1->Session(state,samples);2->Charts(state,samples);3->AI(state);4->History(state);5->Safety(state);else->Logs(state)}'
new_when='when(tab){0->Overview(state);1->Session(state,samples);2->Charts(state,samples);3->AI(state);4->History(state);5->Safety(state);6->BugHealth(state.bugHealth);else->Logs(state)}'
if old_when not in s: raise SystemExit('R9_BUG_UI_FAIL=when-anchor')
s=s.replace(old_when,new_when,1)

insert='''\n@Composable fun BugHealth(b:BugHealthState){\n    val clipboard=LocalClipboardManager.current\n    val status=if(b.openBug) "OPEN" else b.health.ifBlank{"UNKNOWN"}\n    Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)){\n        BoxCard("BUG & HEALTH","Status: $status\\nSeverity: ${b.severity}\\nComponent: ${b.component.ifBlank{"—"}}\\nCode: ${b.code.ifBlank{"—"}}\\nEvent ID: ${b.eventId.ifBlank{"—"}}")\n        BoxCard("OBSERVED FACTS",b.facts.ifBlank{b.summary.ifBlank{"No official DJAEGER bug facts published."}},true)\n        BoxCard("CAUSE HYPOTHESIS",b.hypothesis.ifBlank{"No hypothesis published. Hypotheses are explanatory only and are not the source of bug truth."},true)\n        BoxCard("ACTION / RECOVERY","Action: ${b.action.ifBlank{"—"}}\\nRecovery: ${b.recovery.ifBlank{"—"}}\\nDecision ID: ${b.decisionId.ifBlank{"—"}}\\nTransaction ID: ${b.transactionId.ifBlank{"—"}}")\n        BoxCard("RECENT BUG EVENTS",b.recentEvents.ifBlank{"No bug events recorded."},true)\n        Button(onClick={clipboard.setText(AnnotatedString(BugHealthParser.diagnosticReport(b)))},modifier=Modifier.fillMaxWidth()){Text("COPY DIAGNOSTIC REPORT")}\n    }\n}\n'''
anchor='@Composable fun Session(s:RuntimeState,samples:List<Sample>){'
if anchor not in s: raise SystemExit('R9_BUG_UI_FAIL=session-anchor')
s=s.replace(anchor,insert+'\n'+anchor,1)
p.write_text(s)
print('R9_BUG_HEALTH_INTEGRATION=PASS')
