from pathlib import Path

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

m=main.read_text(); r=repo.read_text(); b=build.read_text()

# 1) Session truth is independent from telemetry/frame freshness.
old='''        val runtimeTtlSec=if(activeClaim) 5L else 15L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec\n        val volatileFresh=runtimeFresh || (activeClaim && fresh)\n'''
new='''        val runtimeTtlSec=15L\n        val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..runtimeTtlSec\n        // SYNC2: ACTIVE/GAME/WINDOW are session truth from atomic runtime.\n        // Telemetry/frame staleness may mark metrics stale, never demote a live session.\n        val sessionFresh=runtimeFresh\n'''
assert old in r
r=r.replace(old,new,1)
old='''            active=if(volatileFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",\n            game=if(volatileFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            window=if(volatileFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",\n'''
new='''            active=if(sessionFresh) (rt["ACTIVE"] ?: rt["active"] ?: "0") else "0",\n            game=if(sessionFresh) (rt["GAME"] ?: rt["game"] ?: "NA") else "NA",\n            window=if(sessionFresh) (rt["WINDOW_MODE"] ?: rt["window_mode"] ?: "INACTIVE") else "INACTIVE",\n'''
assert old in r
r=r.replace(old,new,1)

# 2) UI stale semantics use runtime freshness only. WAITING GAME means fresh active=0.
old='''private fun runtimeStateStale(s:RuntimeState):Boolean{\n    val ttl=if(s.active=="1")5L else 15L\n    val runtimeStale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>ttl\n    return if(s.active=="1") !s.sampleFresh else runtimeStale\n}\n'''
new='''private fun runtimeStateStale(s:RuntimeState):Boolean{\n    return s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>15L\n}\n'''
assert old in m
m=m.replace(old,new,1)
old='''    val sessionState=when{stale->"UNKNOWN";s.active=="1"->"ACTIVE";else->"WAITING GAME"}\n'''
new='''    val sessionState=when{stale->"UNKNOWN / STALE";s.active=="1"->"ACTIVE";else->"WAITING GAME"}\n'''
assert old in m
m=m.replace(old,new,1)

# 3) Display-order-only change. Preserve every existing Overview card/function.
# Requested exact top order after status:
# THOUGHT -> FPS/FRAME/JANK -> CPU/GPU/SKIN/BATTERY -> NETWORK -> STRATEGI.
start=m.index('@Composable fun Overview(')
end=m.index('\n@Composable fun Session(',start)
ov=m[start:end]
assert ov.count('StrategyCard(s);')==1
assert 'StatusCard(s);ThoughtsCard(s);AgentRebuild3Card(s);Row' in ov
assert 'NetworkCard(s.network);HermesCard(s);' in ov
ov=ov.replace('StrategyCard(s);','',1)
ov=ov.replace('StatusCard(s);ThoughtsCard(s);AgentRebuild3Card(s);Row','StatusCard(s);ThoughtsCard(s);Row',1)
ov=ov.replace('NetworkCard(s.network);HermesCard(s);','NetworkCard(s.network);StrategyCard(s);AgentRebuild3Card(s);HermesCard(s);',1)
m=m[:start]+ov+m[end:]

# 4) Version bump only; matched module stays vc129628.
assert 'versionCode = 12254' in b
assert '0.12.1-rebuild3-lang3-mwfix1-math1-sync1' in b
b=b.replace('versionCode = 12254','versionCode = 12255',1)
b=b.replace('0.12.1-rebuild3-lang3-mwfix1-math1-sync1','0.12.1-rebuild3-lang3-mwfix1-math1-sync2',1)

main.write_text(m); repo.write_text(r); build.write_text(b)
print('SYNC2_SESSION_TRUTH_PATCH=PASS')
print('SYNC2_OVERVIEW_ORDER=THOUGHT>METRICS>THERMAL>NETWORK>STRATEGI')
print('SYNC2_EXISTING_CARDS_PRESERVED=PASS')
print('CONTROL_CENTER_VERSION_CODE=12255')
