#!/usr/bin/env python3
# R29: expose backend detector evidence so hardware failures are no longer guessed.
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'; mapper=root/'app/src/main/java/com/djaeger/controlcenter/ConsolidatedRuntimeMapper.kt'

bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12290',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r29"',bs,count=1); b.write_text(bs)

mp=mapper.read_text()
if 'val detector: String,' not in mp:
    anchor='        val network: String,'; assert anchor in mp,'mapper network field missing'; mp=mp.replace(anchor,anchor+'\n        val detector: String,',1)
if 'detector = s["DETECTOR"]' not in mp:
    anchor='            network = s["NETWORK"].orEmpty(),'; assert anchor in mp,'mapper network assignment missing'; mp=mp.replace(anchor,anchor+'\n            detector = s["DETECTOR"].orEmpty(),',1)
mapper.write_text(mp)

rs=r.read_text()
if 'val detector:String=""' not in rs:
    anchor='data class RuntimeState('; assert anchor in rs,'RuntimeState missing'; rs=rs.replace(anchor,anchor+'val detector:String="",',1)
needle='RuntimeState(\n            runtimeVersion=canonicalRuntimeVersion(mapped.moduleVersion),'
assert needle in rs,'R24 constructor missing'
if 'detector=mapped.detector' not in rs:
    rs=rs.replace(needle,'RuntimeState(\n            detector=mapped.detector,\n            runtimeVersion=canonicalRuntimeVersion(mapped.moduleVersion),',1)
rs=rs.replace('val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..5','val runtimeFresh=runtimeUpdated>0 && (now-runtimeUpdated) in 0..12',1)
r.write_text(rs)

ms=m.read_text().replace('v0.12.1-r28','v0.12.1-r29').replace('LIVE HARDWARE','LIVE HARDWARE + DETECTOR EVIDENCE',1)
ms=ms.replace('val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>5;','val stale=s.updated<=0||(System.currentTimeMillis()/1000-s.updated)>12;',1)
anchor='BoxCard("RUNTIME IDENTITY",runtimeIdentity(s),true);'
assert anchor in ms,'runtime identity card missing'
if 'SESSION DETECTOR' not in ms:
    ms=ms.replace(anchor,anchor+'BoxCard("SESSION DETECTOR",s.detector.ifBlank{"Waiting for R94 detector evidence"},true);',1)
m.write_text(ms)

R=r.read_text(); M=m.read_text(); MP=mapper.read_text(); B=b.read_text()
checks={
 'R29_VERSION':'0.12.1-r29' in B and 'v0.12.1-r29' in M,
 'DETECTOR_MAPPED':'val detector: String' in MP and 's["DETECTOR"]' in MP and 'detector=mapped.detector' in R,
 'DETECTOR_VISIBLE':'BoxCard("SESSION DETECTOR"' in M,
 'RUNTIME_FRESHNESS_BOUNDED':'(now-runtimeUpdated) in 0..12' in R,
 'UI_STALE_BOUNDED':'>12;' in M,
 'R28_RESPONSIVE_TABS':'@Composable fun ResponsiveTabs' in M,
 'R27_LIVE_HARDWARE':all(x in M for x in ['LiveClockRow()','Thermal("CPU TEMP",f.cpuT.toInt()','Thermal("GPU TEMP",f.gpuT.toInt()','Thermal("SKIN",f.skinT.toInt()','Thermal("BATTERY",f.batT.toInt()']),
 'MODULE_VAULT':'GEMINI KEY VAULT • MODULE TRUTH' in M,
 'NO_SECOND_ROOT':'ProcessBuilder("su"' not in MP,
}
for k,v in checks.items(): print(f'{k}={"PASS" if v else "FAIL"}')
bad=[k for k,v in checks.items() if not v]; assert not bad,','.join(bad)
forbidden=['iptables ','ip6tables ','nft ','tc qdisc','settings put global private_dns','> /sys/','tee /sys/']
assert not any(x in R+MP for x in forbidden)
print('R29_DETECTOR_EVIDENCE=CC_SNAPSHOT_ONLY')
print('R29_SESSION_TRUTH=NO_HIDDEN_GUESSING')
