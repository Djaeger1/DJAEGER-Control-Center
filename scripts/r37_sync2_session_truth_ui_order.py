from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

m=main.read_text()
r=repo.read_text()
b=build.read_text()

# 1) Session truth must not be destroyed by telemetry/frame freshness.
old='''        val runtimeTtlSec=if(activeClaim) 5L else 15L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec\n        val volatileFresh=runtimeFresh || (activeClaim && fresh)\n'''
new='''        val runtimeTtlSec=if(activeClaim) 15L else 15L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec\n        // SYNC2: preserve session truth independently from telemetry/frame freshness.\n        // ACTIVE/GAME/WINDOW come from the runtime section of the atomic snapshot.\n        // Stale telemetry or frame data must never demote a live session to WAITING GAME.\n        val sessionFresh=runtimeFresh\n'''
assert old in r
r=r.replace(old,new,1)

old='''            active=if(volatileFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",\n            game=if(volatileFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            window=if(volatileFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",\n'''
new='''            active=if(sessionFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",\n            game=if(sessionFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            window=if(sessionFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",\n'''
assert old in r
r=r.replace(old,new,1)

# 2) UI stale/session semantics: WAITING GAME only when runtime is fresh and explicitly inactive.
old='''private fun runtimeStateStale(s:RuntimeState):Boolean{\n    val ttl=if(s.active=="1")5L else 15L\n    val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl\n    return if(s.active=="1") !s.sampleFresh else runtimeStale\n}\n'''
new='''private fun runtimeStateStale(s:RuntimeState):Boolean{\n    val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>15L\n    return runtimeStale\n}\n'''
assert old in m
m=m.replace(old,new,1)

old='''    val sessionState=when{stale->"UNKNOWN";s.active=="1"->"ACTIVE";else->"WAITING GAME"}\n'''
new='''    val sessionState=when{stale->"UNKNOWN / STALE";s.active=="1"->"ACTIVE";else->"WAITING GAME"}\n'''
assert old in m
m=m.replace(old,new,1)

# 3) Overview order: THOUGHTS -> realtime metrics/network -> STRATEGY.
# Replace Overview function body surgically. It intentionally keeps the same cards/functions.
start=m.index('@Composable fun Overview(')
end=m.index('\n@Composable fun Session(', start)
old_overview=m[start:end]
new_overview='''@Composable fun Overview(s:RuntimeState){\n    val activeFresh=s.active=="1"&&!runtimeStateStale(s)\n    val tel=s.telemetry\n    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())){\n        StatusCard(s)\n        Spacer(Modifier.height(12.dp))\n\n        // SYNC2 requested order: Thoughts first.\n        ThoughtsCard(s)\n        Spacer(Modifier.height(12.dp))\n\n        // Then the realtime metric row + thermal row + Network card (screenshot #2).\n        if(activeFresh){\n            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n                MetricTile("FPS",positiveText(tel.fps,""),Modifier.weight(1f))\n                MetricTile("Frame",positiveText(tel.frameMs," ms"),Modifier.weight(1f))\n                MetricTile("Jank",jankText(tel.jank),Modifier.weight(1f))\n            }\n            Spacer(Modifier.height(8.dp))\n            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){\n                MetricTile("CPU",tempText(tel.cpuT),Modifier.weight(1f),if(tel.cpuT>=60) Red else Green)\n                MetricTile("GPU",tempText(tel.gpuT),Modifier.weight(1f),if(tel.gpuT>=60) Red else Green)\n                MetricTile("Skin",tempText(tel.skinT),Modifier.weight(1f),if(tel.skinT>=45) Amber else Green)\n                MetricTile("Battery",tempText(tel.batT),Modifier.weight(1f),if(tel.batT>=45) Amber else Green)\n            }\n        } else {\n            BoxCard("REALTIME","Session tidak aktif/fresh. Telemetry tidak dipakai untuk menentukan kebenaran session.")\n        }\n        Spacer(Modifier.height(12.dp))\n        NetworkCard(s.network)\n        Spacer(Modifier.height(12.dp))\n\n        // Then Strategy (screenshot #3).\n        StrategyCard(s)\n        Spacer(Modifier.height(12.dp))\n\n        AgentRebuild3Card(s)\n        Spacer(Modifier.height(12.dp))\n        HermesCard(s)\n        Spacer(Modifier.height(12.dp))\n    }\n}\n'''
m=m[:start]+new_overview+m[end:]

# 4) Version bump.
assert 'versionCode = 12254' in b
assert '0.12.1-rebuild3-lang3-mwfix1-math1-sync1' in b
b=b.replace('versionCode = 12254','versionCode = 12255',1)
b=b.replace('0.12.1-rebuild3-lang3-mwfix1-math1-sync1','0.12.1-rebuild3-lang3-mwfix1-math1-sync2',1)

main.write_text(m)
repo.write_text(r)
build.write_text(b)
print('SYNC2_SESSION_TRUTH_PATCH=PASS')
print('SYNC2_OVERVIEW_ORDER=THOUGHTS>REALTIME_NETWORK>STRATEGY')
print('CONTROL_CENTER_VERSION_CODE=12255')
