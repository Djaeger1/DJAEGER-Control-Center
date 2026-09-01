#!/usr/bin/env python3
from pathlib import Path
import re
root=Path('control-center-r2')
b=root/'app/build.gradle.kts'; m=root/'app/src/main/java/com/djaeger/controlcenter/MainActivity.kt'; r=root/'app/src/main/java/com/djaeger/controlcenter/DjaegerRepository.kt'
bs=b.read_text(); bs=re.sub(r'versionCode\s*=\s*\d+','versionCode = 12120',bs,count=1); bs=re.sub(r'versionName\s*=\s*"[^"]+"','versionName = "0.12.1-r12"',bs,count=1); b.write_text(bs)
ms=m.read_text().replace('CONTROL CENTER • v0.12.1-r11 • R78 SYNC • REALTIME 1s','CONTROL CENTER • v0.12.1-r12 • USER DESIGN • REALTIME 1s')
anchor='ThermalRow(s);NetworkCard(s.network);BoxCard("PERFORMANCE"'
if anchor not in ms: raise SystemExit('R12_FAIL=layout-anchor')
ms=ms.replace(anchor,'ThermalRow(s);NetworkCard(s.network);StrategyCompositionCard(s);DecisionPipelineCard(s);OutcomeLearningCard(s);BoxCard("PERFORMANCE"',1)
insert='''\n@Composable fun StrategyCompositionCard(s:RuntimeState){\n    BoxCard("STRATEGY COMPOSITION","Source: module-published truth only\\nCPU LITTLE/BIG • GPU • governors • power/bias • burst/lease • comfort ceiling\\nValidation: Local AI / safety authority\\nValues remain unavailable unless explicitly published by DJAEGER; no reconstructed or guessed clocks.")\n}\n@Composable fun DecisionPipelineCard(s:RuntimeState){\n    BoxCard("DECISION PIPELINE","PROPOSED → VALIDATED / REJECTED → APPLIED → READBACK VERIFIED → OUTCOME\\nControl Center remains observer/orchestrator; authority and capability truth stay in the existing runtime cards.")\n}\n@Composable fun OutcomeLearningCard(s:RuntimeState){\n    BoxCard("OUTCOME + LEARNING","FPS/frame/thermal/power outcomes remain telemetry-backed.\\nLearning samples/confidence/promotion are displayed only when published by the module.\\nFallback decisions remain explicitly identified; Gemini conversation is inert and never direct hardware authority.")\n}\n'''
idx=ms.index('@Composable fun ThermalRow(s:RuntimeState)')
ms=ms[:idx]+insert+ms[idx:]
m.write_text(ms)
print('R12_BASELINE=USER_R11')
print('R12_DESIGN=ADDITIVE')
print('R12_R78=DISABLED')
print('R12_STRATEGY_PIPELINE_OUTCOME=PASS')
