#!/usr/bin/env python3
from pathlib import Path
import re

root=Path('control-center-r2')
b=root/'app/build.gradle.kts'
m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'

bs=b.read_text()
bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12300',bs,count=1)
bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r30"',bs,count=1)
b.write_text(bs)

ms=m.read_text()
ms=ms.replace('CONTROL CENTER • v0.12.1-r29 • TRUTH ATTRIBUTION','CONTROL CENTER • v0.12.1-r30 • HUMAN STRATEGY',1).replace('v0.12.1-r29','v0.12.1-r30')

old='''    BoxCard("THOUGHTS", providerLines+"\\n\\n"+text, true)'''
new='''    fun logToken(line:String,key:String):String{
        val marker="$key="
        val tail=line.substringAfter(marker,"")
        return if(tail.isBlank()) "—" else tail.substringBefore(' ').trim().trim('\\'')
    }
    val policyLine=s.log.lineSequence().filter{it.contains("PREDICTOR POLICY ACTION=")}.lastOrNull().orEmpty()
    val commitLine=s.log.lineSequence().filter{it.contains("CLOUD_STRATEGY_COMMITTED")}.lastOrNull().orEmpty()
    val hierarchyLine=s.log.lineSequence().filter{it.contains("HIERARCHY ") && it.contains(" ACTION=")}.lastOrNull().orEmpty()

    val strategyAction=logToken(policyLine,"ACTION").takeIf{it!="—"}
        ?:logToken(commitLine,"action").takeIf{it!="—"}
        ?:logToken(hierarchyLine,"ACTION")
    val strategyMode=logToken(policyLine,"MODE").takeIf{it!="—"}
        ?:s.strategy.proposal.split(' ').getOrNull(1).orEmpty().ifBlank{"—"}
    val strategyProfile=logToken(policyLine,"ANCHOR").takeIf{it!="—"}
        ?:logToken(commitLine,"profile").takeIf{it!="—"}
        ?:s.strategy.proposal.split(' ').getOrNull(2).orEmpty().ifBlank{"—"}
    val thermalState=logToken(policyLine,"THERMAL")
    val performanceState=logToken(policyLine,"PERF")
    val skin2m=logToken(policyLine,"SKIN2M")
    val fps2m=logToken(policyLine,"FPS2M")
    val review=logToken(policyLine,"DURATION")
    val confidence=logToken(policyLine,"CONF").takeIf{it!="—"}?:s.strategy.confidence.ifBlank{"—"}

    val actionHuman=when(strategyAction.uppercase()){
        "KEEP","HOLD"->"mempertahankan strategi dan envelope resource saat ini"
        "APPLY","CHANGE","ADJUST","TUNE"->"menerapkan penyesuaian resource yang telah dirumuskan"
        "RESTORE"->"mengembalikan resource ke keadaan aman yang telah divalidasi"
        "NONE","—",""->"menjaga kondisi sambil menunggu keputusan berikutnya"
        else->"menjalankan keputusan $strategyAction"
    }
    val sourceHuman=if(strategySource=="LOCAL AI") "Local AI" else strategySource
    val confidenceNote=when(confidence.toDoubleOrNull()){
        null->""
        0.0->" Keyakinan prediksi saat ini 0%, sehingga Local AI tetap wajib memvalidasi sebelum eksekusi."
        else->" Tingkat keyakinan strategi: $confidence%."
    }
    val humanStrategy="BAHASA MANUSIA\\n"+
        "$sourceHuman memilih untuk $actionHuman. "+
        "Rencana resource: CPU little ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz, "+
        "CPU big ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz, dan GPU ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz. "+
        "Tujuannya menjaga frame pacing dan performa berkelanjutan tanpa perubahan yang tidak diperlukan. "+
        "Local AI tetap menjadi validator dan executor-side safety authority.$confidenceNote"

    val predictionText=when{
        skin2m!="—" && fps2m!="—"->"Skin 2m: $skin2m°C • FPS 2m: $fps2m"
        skin2m!="—"->"Skin 2m: $skin2m°C"
        fps2m!="—"->"FPS 2m: $fps2m"
        else->"Belum tersedia"
    }
    val riskText=when{
        thermalState!="—" && performanceState!="—"->"Thermal: $thermalState • Performance: $performanceState"
        thermalState!="—"->"Thermal: $thermalState"
        performanceState!="—"->"Performance: $performanceState"
        else->"Belum tersedia"
    }
    val technicalStrategy="STRATEGI\\n"+
        "Keputusan: $strategyAction\\n"+
        "Profil / mode: $strategyProfile / $strategyMode\\n"+
        "CPU little: ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz\\n"+
        "CPU big: ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz\\n"+
        "GPU: ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz\\n"+
        "Prediksi: $predictionText\\n"+
        "Risiko: $riskText\\n"+
        "Confidence: $confidence%\\n"+
        "Review ulang: $review\\n"+
        "Validasi Local AI: ${s.strategy.validation.ifBlank{"—"}}"

    BoxCard("THOUGHTS", providerLines+"\\n\\n"+humanStrategy+"\\n\\n"+technicalStrategy, true)'''
assert old in ms, 'R30 R29 THOUGHTS card anchor missing'
ms=ms.replace(old,new,1)

assert 'BAHASA MANUSIA\\n' in ms
assert 'STRATEGI\\n' in ms
assert 'Keputusan: $strategyAction' in ms
assert 'CPU little: ${s.strategy.cpuLittleMin}-${s.strategy.cpuLittleMax} kHz' in ms
assert 'CPU big: ${s.strategy.cpuBigMin}-${s.strategy.cpuBigMax} kHz' in ms
assert 'GPU: ${s.strategy.gpuMin}-${s.strategy.gpuMax} MHz' in ms
assert 'Validasi Local AI: ${s.strategy.validation.ifBlank{"—"}}' in ms
assert 'Local AI tetap menjadi validator dan executor-side safety authority.' in ms
assert 'BoxCard("THOUGHTS", providerLines+"\\n\\n"+humanStrategy+"\\n\\n"+technicalStrategy, true)' in ms
assert 'providerLines+"\\n\\n"+text' not in ms
m.write_text(ms)

print('R30_LANGUAGE=INDONESIAN_HUMAN_SUMMARY')
print('R30_STRATEGY=STRUCTURED_TECHNICAL_VIEW')
print('R30_ACTION=CONTROLLER_LOG_TRUTH')
print('R30_CPU_GPU=STRATEGY_TRUTH_FIELDS')
print('R30_PREDICTION_RISK=POLICY_EVENT_FIELDS')
print('R30_LOCAL_VALIDATOR=VISIBLE')
print('R30_EXTRA_ROOT_POLLING=0')
