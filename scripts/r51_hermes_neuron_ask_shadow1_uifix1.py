from pathlib import Path
import re

root=Path('control-center-r2')
main=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'
repo=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
build=root/'app/build.gradle.kts'

M=main.read_text(); R=repo.read_text(); B=build.read_text()

# Exact HERMES-NEURON-ASK-SHADOW1 identity must remain paired to the existing module contract.
assert 'versionCode = 12261' in B
assert 'hermescloud1-workloadfinal1-neurongov1-askhermes1' in B
assert 'Ask DJAEGER Hermes' in M
assert 'HERMES CONVERSATION' in M
assert 'HERMES_NEURON_USED_EST' in M
assert 'djaeger-hermes-cloud chat-stdin' in R

# 1) Header-only cleanup requested by user.
long_header='CONTROL CENTER • REBUILD3 • LANG3 • MWFIX2 • ATTR1 • MATH1 • KERNEL1 • SYSFS1 • LOOPFIX1 • GAMEREG1 • SHAREDINT1 • HERMESCLOUD1 • WORKLOADFINAL1'
assert long_header in M
M=M.replace(long_header,'CONTROL CENTER',1)

# 2) APK-only transient network display hold. No network engine/module changes.
old_state='data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false)'
new_state='data class NetworkState(val ping:String="—",val avg:String="—",val p95:String="—",val jitter:String="—",val loss:String="—",val quality:String="STALE/INACTIVE",val fresh:Boolean=false,val held:Boolean=false,val lastAgeSec:Long=0L)'
assert old_state in R
R=R.replace(old_state,new_state,1)

cm=re.search(r'class DjaegerRepository[^\{]*\{',R)
assert cm
p=cm.end()
R=R[:p]+'\n    private var lastGoodNetwork:NetworkState?=null\n    private var lastGoodNetworkAt:Long=0L'+R[p:]

network_pattern=re.compile(r'''        val network = if\(netFresh\) NetworkState\(\n            ping=nkv\["PING_CURRENT_MS"\] \?: "—",\n            avg=nkv\["PING_AVG_MS"\] \?: "—",\n            p95=nkv\["PING_P95_MS"\] \?: "—",\n            jitter=nkv\["JITTER_MS"\] \?: "—",\n            loss=nkv\["PACKET_LOSS_PCT"\] \?: "—",\n            quality=nkv\["QUALITY"\] \?: "UNKNOWN",\n            fresh=true\n        \) else NetworkState\(\)''')
m=network_pattern.search(R)
assert m, 'R51_FAIL=network-baseline-anchor'
replacement='''        val liveNetwork = if(netFresh) NetworkState(
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
R=R[:m.start()]+replacement+R[m.end():]

ui_start=M.index('@Composable fun NetworkCard(n:NetworkState)')
ui_end=M.index('@Composable fun NetworkMetric',ui_start)
ui=M[ui_start:ui_end]
assert 'val clipboard=LocalClipboardManager.current' in ui
ui=ui.replace('val clipboard=LocalClipboardManager.current','val clipboard=LocalClipboardManager.current\n    val show=n.fresh||n.held',1)
assert ui.count('if(n.fresh)') >= 6
ui=ui.replace('if(n.fresh)','if(show)')
assert 'color=if(show) Green else Muted' in ui
ui=ui.replace('color=if(show) Green else Muted','color=when{n.fresh->Green;n.held->Amber;else->Muted}',1)
M=M[:ui_start]+ui+M[ui_end:]

# Strict regression / synchronization gates.
assert long_header not in M
assert 'CONTROL CENTER' in M
assert 'Ask DJAEGER Gemini' in M and 'Ask DJAEGER Hermes' in M
assert 'HERMES CONVERSATION' in M
assert 'HERMES_NEURON_USED_EST' in M and 'HERMES_NEURON_LIMIT' in M and 'HERMES_NEURON_TIER' in M
assert 'djaeger-hermes-cloud chat-stdin' in R and 'djaeger-hermes-cloud chat-clear' in R
assert 'holdAge in 1L..10L' in R and 'held=true' in R
assert 'n.fresh||n.held' in M
assert '/sys/' not in R and '/proc/sys/' not in R
assert 'versionCode = 12261' in B
assert 'hermescloud1-workloadfinal1-neurongov1-askhermes1' in B

main.write_text(M); repo.write_text(R)
# build.gradle intentionally unchanged: exact SHADOW1 pairing/version identity preserved.

print('R51_SHADOW1_UIFIX=PASS')
print('HEADER=CONTROL_CENTER_ONLY')
print('NETWORK_TRANSIENT_HOLD_SEC=10')
print('NETWORK_HOLD_LABEL=EXPLICIT')
print('ASK_HERMES=PRESERVED')
print('NEURON_CARD=PRESERVED')
print('MODULE_CHANGE=NONE')
print('CONTROL_CENTER_VC=12261')
