from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

m=main.read_text()
r=repo.read_text()
b=build.read_text()

# Hard baseline identity: APK-only patch, module pair must remain untouched/matched.
assert 'versionCode = 12261' in b
assert 'versionName = "0.12.1-rebuild3-hk1-sysfs1-ccsync1-loopfix1-gamereg1-sharedint1-hermescloud1-workloadfinal1"' in b
assert 'VC129637 / VC12261' in m
assert 'REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1' in m

# 1) UI header only: remove the long build identity from the top overlay.
long_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1 • WORKLOADFINAL1'
assert long_header in m
m=m.replace(long_header,'CONTROL CENTER',1)

# 2) Network transient-gap smoothing in APK read/UI path only.
# Never fabricate zeroes. A prior valid sample may be displayed for <=10 seconds only
# while the runtime session is still active, and is explicitly marked HOLD (amber).
old_state='data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false)'
new_state='data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false,val held:Boolean=false,val lastAgeSec:Long=0L)'
assert old_state in r
r=r.replace(old_state,new_state,1)

# Add a tiny in-memory cache inside the APK repository only.
class_match=re.search(r'class DjaegerRepository[^\{]*\{',r)
assert class_match
pos=class_match.end()
r=r[:pos]+'\n    private var lastGoodNetwork:NetworkState?=null\n    private var lastGoodNetworkAt:Long=0L'+r[pos:]

network_pattern=re.compile(r'''        val network = if\(netFresh\) NetworkState\(\n            ping=nkv\["PING_CURRENT_MS"\] \?: "—",\n            avg=nkv\["PING_AVG_MS"\] \?: "—",\n            p95=nkv\["PING_P95_MS"\] \?: "—",\n            jitter=nkv\["JITTER_MS"\] \?: "—",\n            loss=nkv\["PACKET_LOSS_PCT"\] \?: "—",\n            quality=nkv\["QUALITY"\] \?: "UNKNOWN",\n            fresh=true\n        \) else NetworkState\(\)''')
match=network_pattern.search(r)
assert match, 'network-baseline-anchor-not-found'
new_network='''        val liveNetwork = if(netFresh) NetworkState(
            ping=nkv["PING_CURRENT_MS"] ?: "—",
            avg=nkv["PING_AVG_MS"] ?: "—",
            p95=nkv["PING_P95_MS"] ?: "—",
            jitter=nkv["JITTER_MS"] ?: "—",
            loss=nkv["PACKET_LOSS_PCT"] ?: "—",
            quality=nkv["QUALITY"] ?: "UNKNOWN",
            fresh=true,
            held=false,
            lastAgeSec=0L
        ) else null
        if(liveNetwork!=null){lastGoodNetwork=liveNetwork;lastGoodNetworkAt=now}
        val runtimeSessionActive=(rt["ACTIVE"] ?: rt["active"] ?: "0")=="1"
        val holdAge=if(lastGoodNetworkAt>0L) now-lastGoodNetworkAt else Long.MAX_VALUE
        val network=when{
            liveNetwork!=null -> liveNetwork
            runtimeSessionActive && lastGoodNetwork!=null && holdAge in 1L..10L -> lastGoodNetwork!!.copy(
                fresh=false,
                held=true,
                lastAgeSec=holdAge,
                quality="${lastGoodNetwork!!.quality} • HOLD ${holdAge}s"
            )
            else -> NetworkState()
        }'''
r=r[:match.start()]+new_network+r[match.end():]

# Modify NetworkCard only. Other cards and Overview order remain byte-for-byte source-equivalent.
ui_start=m.index('@Composable fun NetworkCard(n:NetworkState)')
ui_end=m.index('@Composable fun NetworkMetric',ui_start)
ui=m[ui_start:ui_end]
assert 'val clipboard=LocalClipboardManager.current' in ui
ui=ui.replace('val clipboard=LocalClipboardManager.current','val clipboard=LocalClipboardManager.current\n    val show=n.fresh||n.held',1)
assert ui.count('if(n.fresh)') >= 6
ui=ui.replace('if(n.fresh)','if(show)')
old_quality='color=if(show) Green else Muted'
assert old_quality in ui
ui=ui.replace(old_quality,'color=when{n.fresh->Green;n.held->Amber;else->Muted}',1)
m=m[:ui_start]+ui+m[ui_end:]

# Regression gates: no module/hardware authority added and matched identity is unchanged.
assert long_header not in m
assert 'CONTROL CENTER' in m
assert 'VC129637 / VC12261' in m
assert 'versionCode = 12261' in b
assert 'workloadfinal1' in b
assert 'ProcessBuilder("su"' not in m
assert '/sys/' not in m and '/proc/sys/' not in m
assert 'HOLD ${holdAge}s' in r
assert 'holdAge in 1L..10L' in r
assert 'n.fresh||n.held' in m

main.write_text(m)
repo.write_text(r)
# build.gradle.kts intentionally not written: exact version/contract preserved.

print('APK_UIFIX1=PASS')
print('HEADER=CONTROL_CENTER_ONLY')
print('NETWORK_TRANSIENT_HOLD_SEC=10')
print('NETWORK_STALE_LABEL=EXPLICIT_HOLD')
print('MODULE_CHANGE=NONE')
print('MODULE_VC=129637')
print('CONTROL_CENTER_VC=12261')
print('BASELINE=WORKLOADFINAL1')
