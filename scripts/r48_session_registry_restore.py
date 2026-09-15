from pathlib import Path

main = Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
m = main.read_text()

# WORKLOADFINAL1 must expose BOTH sides of the dual registry. The original
# integration only added a compact summary and left the user with the GAME
# editor, which made the APP registry look missing.
anchor = '@Composable fun GameRegistryCard(repo:DjaegerRepository){'
assert anchor in m, 'GameRegistryCard anchor not found'

app_card = r'''@Composable fun AppRegistryListCard(s:RuntimeState){
    data class AppRow(val pkg:String,val profile:String,val name:String)
    val rows=s.appRegistry.lineSequence().mapNotNull{line->
        val raw=line.trim()
        if(raw.isBlank()||raw.startsWith("#")) null else {
            val p=raw.split('\t')
            val pkg=p.getOrNull(0).orEmpty().trim()
            if(pkg.isBlank()) null else AppRow(
                pkg=pkg,
                profile=p.getOrNull(1).orEmpty().ifBlank{"APP_INTERACTIVE"},
                name=p.getOrNull(2).orEmpty().ifBlank{pkg}
            )
        }
    }.toList()
    val legacyGame=s.gameRegistryManual.lineSequence().mapNotNull{line->
        line.trim().takeIf{it.isNotBlank()&&!it.startsWith("#")}?.split('\t')?.firstOrNull()?.trim()?.takeIf{it.isNotBlank()}
    }.toSet()

    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){
        Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            Text("APP REGISTRY • MANUAL",color=Green,fontWeight=FontWeight.Bold)
            Text("Registry APP terpisah dari GAME. APP tetap dipahami/diamati DJAEGER, tetapi tidak menerima game semantics atau policy hardware game.",color=Muted,style=MaterialTheme.typography.bodySmall)
            if(rows.isEmpty()){
                Text("Belum ada APP manual di app_registry.tsv.",color=Muted)
            }else{
                rows.forEach{e->
                    Column(Modifier.fillMaxWidth()){
                        Text(e.name,color=MaterialTheme.colorScheme.onSurface,fontWeight=FontWeight.SemiBold)
                        Text(e.pkg,color=Muted,style=MaterialTheme.typography.bodySmall)
                        Text("APP • ${e.profile} • OBSERVE ONLY",color=Green,style=MaterialTheme.typography.labelSmall)
                        if(e.pkg in legacyGame) Text("APP WINS • legacy GAME conflict masih tercatat",color=Red,style=MaterialTheme.typography.labelSmall)
                    }
                    HorizontalDivider()
                }
            }
        }
    }
}

'''
m = m.replace(anchor, app_card + anchor, 1)

# Keep the established Session architecture, but make the canonical APP list
# visible before the GAME editor. No existing monitor cards are removed.
old_session = '''        DualRegistrySummaryCard(s)\n        GameRegistryCard(repo)\n'''
new_session = '''        DualRegistrySummaryCard(s)\n        AppRegistryListCard(s)\n        GameRegistryCard(repo)\n'''
assert old_session in m, 'Session dual-registry anchor not found'
m = m.replace(old_session, new_session, 1)

# ENGINE / SESSION previously treated game-session ACTIVE as if it were the
# only kind of active workload. Preserve the backend GAME truth, but expose the
# current APP/SYSTEM workload and its profile so APP_INTERACTIVE no longer
# looks inactive merely because game execution is intentionally blocked.
old_state = '    val sessionState=when{stale->"UNKNOWN / STALE";s.active=="1"->"ACTIVE";else->"WAITING GAME"}'
new_state = '''    val workloadClass=envField(s.workloadContext,"WORKLOAD_CLASS").ifBlank{envField(s.workloadContext,"SUBJECT_CLASS")}.uppercase()\n    val workloadPackage=envField(s.workloadContext,"PACKAGE").ifBlank{"UNKNOWN"}\n    val workloadProfile=envField(s.workloadContext,"WORKLOAD_PROFILE").ifBlank{"UNKNOWN"}\n    val sessionState=when{\n        stale->"UNKNOWN / STALE"\n        s.active=="1"->"GAME ACTIVE"\n        workloadClass=="APP"->"APP ACTIVE • OBSERVE ONLY"\n        workloadClass=="SYSTEM"->"SYSTEM ACTIVE • OBSERVE ONLY"\n        else->"WAITING GAME"\n    }'''
assert old_state in m, 'StatusCard session-state anchor not found'
m = m.replace(old_state, new_state, 1)

old_profile = '''    val profile=if(s.active=="1") s.telemetry.profile else "—"'''
new_profile = '''    val profile=when{\n        s.active=="1"->s.telemetry.profile\n        workloadClass=="APP"||workloadClass=="SYSTEM"->workloadProfile\n        else->"—"\n    }\n    val gameExecution=if(s.active=="1"&&workloadClass=="GAME") "ACTIVE" else "BLOCKED / OBSERVE ONLY"'''
assert old_profile in m, 'StatusCard profile anchor not found'
m = m.replace(old_profile, new_profile, 1)

old_body = '''    BoxCard("ENGINE / SESSION",if(s.installed)"Engine: $engine • age $ageText\\nSession: $sessionState\\nModule: ${compactModuleVersion(s.moduleVersion)}\\nGame: $game\\nWindow: $window\\nProfile: $profile\\nLast device sample: $sample\\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")'''
new_body = '''    BoxCard("ENGINE / SESSION",if(s.installed)"Engine: $engine • age $ageText\\nSession: $sessionState\\nModule: ${compactModuleVersion(s.moduleVersion)}\\nGame: $game\\nWindow: $window\\nProfile: $profile\\nWorkload: $workloadClass • $workloadPackage\\nGame execution: $gameExecution\\nLast device sample: $sample\\nController PID: ${s.controllerPid.ifBlank{"—"}} • Predictor PID: ${s.predictorPid.ifBlank{"—"}}" else "DJAEGER module not found")'''
assert old_body in m, 'StatusCard body anchor not found'
m = m.replace(old_body, new_body, 1)

main.write_text(m)

# Hard UI regression gates. Build must fail if any of the reported breakages
# returns: missing APP list, misleading WAITING GAME for APP/SYSTEM, unreadable
# registry text, or accidental removal/reordering of Session registry surfaces.
M = main.read_text()
assert '@Composable fun AppRegistryListCard(s:RuntimeState)' in M
assert 'Text("APP REGISTRY • MANUAL",color=Green' in M
assert 'APP ACTIVE • OBSERVE ONLY' in M
assert 'SYSTEM ACTIVE • OBSERVE ONLY' in M
assert 'GAME ACTIVE' in M
assert 'Workload: $workloadClass • $workloadPackage' in M
assert 'Game execution: $gameExecution' in M
assert 'workloadClass=="APP"||workloadClass=="SYSTEM"->workloadProfile' in M
assert 'DualRegistrySummaryCard(s)\n        AppRegistryListCard(s)\n        GameRegistryCard(repo)' in M
assert 'Text("GAME REGISTRY • MANUAL",color=Green' in M
assert 'Text(e.displayName,color=MaterialTheme.colorScheme.onSurface' in M
session = M[M.index('@Composable fun Session(s:RuntimeState'):M.index('private fun monitorPhase',M.index('@Composable fun Session(s:RuntimeState'))]
assert session.index('DualRegistrySummaryCard(s)') < session.index('AppRegistryListCard(s)') < session.index('GameRegistryCard(repo)')

print('WORKLOADFINAL1_SESSION_REGISTRY_RESTORE=PASS')
print('APP_REGISTRY_FULL_LIST=VISIBLE')
print('GAME_REGISTRY_PRESERVED=YES')
print('APP_SYSTEM_SESSION_LABELS=OBSERVE_ONLY')
print('APP_SYSTEM_PROFILE=VISIBLE')
print('WORKLOAD_PACKAGE=VISIBLE')
print('GAME_EXECUTION_SCOPE=VISIBLE')
print('BACKEND_AUTHORITY_CHANGED=NO')
