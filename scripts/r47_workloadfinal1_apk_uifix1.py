from pathlib import Path
import hashlib

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

class_anchor='class DjaegerRepository'
ci=r.index(class_anchor)
brace=r.index('{',ci)
r=r[:brace+1]+'\n    private var lastGoodNetwork:NetworkState?=null\n    private var lastGoodNetworkAt:Long=0L'+r[brace+1:]

old_network='val network=if(netFresh) NetworkState(nkv["PING_CURRENT_MS"]?:"—",nkv["PING_AVG_MS"]?:"—",nkv["PING_P95_MS"]?:"—",nkv["JITTER_MS"]?:"—",nkv["PACKET_LOSS_PCT"]?:"—",nkv["QUALITY"]?:"UNKNOWN",true) else NetworkState()'
new_network='''val liveNetwork=if(netFresh) NetworkState(nkv["PING_CURRENT_MS"]?:"—",nkv["PING_AVG_MS"]?:"—",nkv["PING_P95_MS"]?:"—",nkv["JITTER_MS"]?:"—",nkv["PACKET_LOSS_PCT"]?:"—",nkv["QUALITY"]?:"UNKNOWN",true,false,0L) else null
        if(liveNetwork!=null){lastGoodNetwork=liveNetwork;lastGoodNetworkAt=nowNet}
        val runtimeSessionActive=(rt["ACTIVE"]?:rt["active"]?:"0")=="1"
        val holdAge=if(lastGoodNetworkAt>0L) nowNet-lastGoodNetworkAt else Long.MAX_VALUE
        val network=when{
            liveNetwork!=null->liveNetwork
            runtimeSessionActive&&lastGoodNetwork!=null&&holdAge in 1L..10L->lastGoodNetwork!!.copy(fresh=false,held=true,lastAgeSec=holdAge,quality="${lastGoodNetwork!!.quality} • HOLD ${holdAge}s")
            else->NetworkState()
        }'''
assert old_network in r
r=r.replace(old_network,new_network,1)

old_ui='''@Composable fun NetworkCard(n:NetworkState){
    val clipboard=LocalClipboardManager.current
    val body="Ping ${n.ping} ms • Avg ${n.avg} ms • P95 ${n.p95} ms • Jitter ${n.jitter} ms • Loss ${n.loss}% • Quality ${n.quality}"
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("NETWORK",color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString(body))}){Text("COPY")}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){NetworkMetric("Ping",if(n.fresh) "${n.ping} ms" else "—");NetworkMetric("Avg",if(n.fresh) "${n.avg} ms" else "—");NetworkMetric("P95",if(n.fresh) "${n.p95} ms" else "—");NetworkMetric("Jitter",if(n.fresh) "${n.jitter} ms" else "—");NetworkMetric("Loss",if(n.fresh) "${n.loss}%" else "—")}
        Spacer(Modifier.height(8.dp));Text("Quality: ${n.quality}",color=if(n.fresh) Green else Muted,fontWeight=FontWeight.Bold)
    }}
}'''
new_ui='''@Composable fun NetworkCard(n:NetworkState){
    val clipboard=LocalClipboardManager.current
    val show=n.fresh||n.held
    val body="Ping ${if(show)n.ping else "—"} ms • Avg ${if(show)n.avg else "—"} ms • P95 ${if(show)n.p95 else "—"} ms • Jitter ${if(show)n.jitter else "—"} ms • Loss ${if(show)n.loss else "—"}% • Quality ${n.quality}"
    val qualityColor=when{n.fresh->Green;n.held->Amber;else->Muted}
    Card(Modifier.fillMaxWidth(),colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(14.dp)){Column(Modifier.padding(14.dp)){
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("NETWORK",color=Green,fontWeight=FontWeight.Bold);TextButton(onClick={clipboard.setText(AnnotatedString(body))}){Text("COPY")}}
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){NetworkMetric("Ping",if(show) "${n.ping} ms" else "—");NetworkMetric("Avg",if(show) "${n.avg} ms" else "—");NetworkMetric("P95",if(show) "${n.p95} ms" else "—");NetworkMetric("Jitter",if(show) "${n.jitter} ms" else "—");NetworkMetric("Loss",if(show) "${n.loss}%" else "—")}
        Spacer(Modifier.height(8.dp));Text("Quality: ${n.quality}",color=qualityColor,fontWeight=FontWeight.Bold)
    }}
}'''
assert old_ui in m
m=m.replace(old_ui,new_ui,1)

# Regression gates: no module/hardware authority added and matched identity is unchanged.
assert long_header not in m
assert 'Text("CONTROL CENTER"' in m or '"CONTROL CENTER"' in m
assert 'VC129637 / VC12261' in m
assert 'versionCode = 12261' in b
assert 'workloadfinal1' in b
assert 'ProcessBuilder("su"' not in m
assert '/sys/' not in m and '/proc/sys/' not in m
assert 'HOLD ${holdAge}s' in r
assert 'holdAge in 1L..10L' in r

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
