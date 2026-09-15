from pathlib import Path

main = Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
m = main.read_text()

# WORKLOADFINAL1 is additive. It must never interrupt the user's established
# Overview sequence between ENGINE / SESSION and THOUGHT.
bad = 'StatusCard(s);WorkloadIntelligenceCard(s);ThoughtsCard(s);'
good = 'StatusCard(s);ThoughtsCard(s);'
assert bad in m, 'WORKLOADFINAL1 misplaced Overview insertion not found'
m = m.replace(bad, good, 1)

# Preserve every existing Overview card in its established order, then append
# the new workload truth card at the end. No existing card is moved or removed.
tail = 'BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true)}}'
replacement = 'BoxCard("FRAME INTELLIGENCE • RECENT",s.frameIntel.ifBlank{"No frame history yet"},true);WorkloadIntelligenceCard(s)}}'
assert tail in m, 'Overview tail anchor not found'
m = m.replace(tail, replacement, 1)

main.write_text(m)

# Hard regression gate: the pre-WORKLOADFINAL1 Overview sequence must remain
# byte-order equivalent at the call level. WORKLOAD is allowed exactly once,
# and only after the complete existing sequence.
M = main.read_text()
start = M.index('@Composable fun Overview(s:RuntimeState)')
end = M.index('private fun compactModuleVersion', start)
ov = M[start:end]

expected = [
    'StatusCard(s)',
    'ThoughtsCard(s)',
    'Metric("FPS"',
    'ThermalRow(s)',
    'NetworkCard(s.network)',
    'StrategyCard(s)',
    'AgentRebuild3Card(s)',
    'HermesCloudCard(s)',
    'KernelAgentSyncCard(s)',
    'HermesCard(s)',
    'HumanComfortHcc1Card(s)',
    'ContextVNextCard(s)',
    'MemoryVNextCard(s)',
    'ReasoningV2Card(s)',
    'SkillsVNextCard(s)',
    'LearningResearchV2Card(s)',
    'OutcomeLearningCard(s)',
    'StrategyCompositionCard(s)',
    'DecisionPipelineCard(s)',
    'BoxCard("PERFORMANCE"',
    'BoxCard("POWER"',
    'BoxCard("FRAME INTELLIGENCE • RECENT"',
    'WorkloadIntelligenceCard(s)',
]
positions = [ov.index(x) for x in expected]
assert positions == sorted(positions), positions
assert ov.count('WorkloadIntelligenceCard(s)') == 1
assert 'StatusCard(s);ThoughtsCard(s);' in ov
assert 'StatusCard(s);WorkloadIntelligenceCard(s);' not in ov

print('WORKLOADFINAL1_OVERVIEW_ORDER_FIX=PASS')
print('EXISTING_OVERVIEW_SEQUENCE=PRESERVED')
print('WORKLOAD_CARD=ADDITIVE_AT_END')
