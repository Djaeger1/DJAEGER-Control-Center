from pathlib import Path

main=Path('control-center-r2/app/src/main/java/com/djaeger/controlcenter/MainActivity.kt')
m=main.read_text()

start=m.index('@Composable fun HermesCloudCard(s:RuntimeState){')
end=m.index('@Composable fun HermesCard(s:RuntimeState){',start)

fixed=r'''@Composable fun HermesCloudCard(s:RuntimeState){
    val backend=envField(s.brain,"HERMES_BACKEND").ifBlank{"LOCAL"}
    val state=envField(s.brain,"HERMES_CLOUD_STATE").ifBlank{"UNAVAILABLE"}
    val auth=envField(s.brain,"HERMES_CLOUD_AUTH").ifBlank{"UNKNOWN"}
    val route=envField(s.brain,"HERMES_CLOUD_ROUTE").ifBlank{"—"}
    val model=envField(s.brain,"HERMES_CLOUD_MODEL").ifBlank{"—"}
    val latency=envField(s.brain,"HERMES_CLOUD_LATENCY_MS").ifBlank{"—"}
    val http=envField(s.brain,"HERMES_CLOUD_HTTP_CODE").ifBlank{"—"}
    val fallback=envField(s.brain,"HERMES_CLOUD_FALLBACK_USED").ifBlank{"NO"}
    val requestId=envField(s.brain,"HERMES_CLOUD_REQUEST_ID").ifBlank{"—"}
    val reason=envField(s.brain,"HERMES_CLOUD_REASON").ifBlank{"—"}
    val currentBrain=envField(s.brain,"CURRENT_BRAIN").ifBlank{"—"}
    val contract=envField(s.controlCenterSync,"HERMES_CLOUD").ifBlank{"UNPUBLISHED"}
    val role=envField(s.controlCenterSync,"HERMES_CLOUD_ROLE").ifBlank{"REMOTE_BACKEND_OF_HERMES_H2_NOT_THIRD_BRAIN"}
    val body="Contract: $contract\nEndpoint: hermes-cloud-djaeger.moclomper.workers.dev\nHERMES H2 backend: $backend\nCloud state: $state\nAccess key: $auth • secret never displayed\nRoute: $route\nModel: $model\nLatency: $latency ms • HTTP: $http\nReason: $reason\nCloud tier fallback used: $fallback\nRequest ID: $requestId\nCurrent brain: $currentBrain\nRole: $role\nPolicy: Gemini primary → HERMES H2 cloud → HERMES H2 local → native failsafe\nCloud direct hardware authority: NONE\nHardware executor: AI AGENT A1 ONLY"
    BoxCard("HERMES CLOUD • ONE HERMES • HERMESCLOUD1",body,true)
}

'''

m=m[:start]+fixed+m[end:]
main.write_text(m)

M=main.read_text()
cloud=M[M.index('@Composable fun HermesCloudCard'):M.index('@Composable fun HermesCard',M.index('@Composable fun HermesCloudCard'))]
assert 'HERMES_CLOUD_REASON' in cloud
assert 'Reason: $reason' in cloud
# A literal double-backslash+n renders as visible "\\n". Only normal Kotlin \n escapes are allowed.
assert r'\\n' not in cloud
assert 'Hardware executor: AI AGENT A1 ONLY' in cloud
assert 'secret never displayed' in cloud

# Do not allow this display-only repair to move any Overview card.
ov=M[M.index('@Composable fun Overview(s:RuntimeState)'):M.index('private fun compactModuleVersion',M.index('@Composable fun Overview(s:RuntimeState)'))]
expected=['StatusCard(s)','ThoughtsCard(s)','Metric("FPS"','ThermalRow(s)','NetworkCard(s.network)','StrategyCard(s)','AgentRebuild3Card(s)','HermesCloudCard(s)','KernelAgentSyncCard(s)','HermesCard(s)','HumanComfortHcc1Card(s)','ContextVNextCard(s)','MemoryVNextCard(s)','ReasoningV2Card(s)','SkillsVNextCard(s)','LearningResearchV2Card(s)','OutcomeLearningCard(s)','StrategyCompositionCard(s)','DecisionPipelineCard(s)','BoxCard("PERFORMANCE"','BoxCard("POWER"','BoxCard("FRAME INTELLIGENCE • RECENT"','WorkloadIntelligenceCard(s)']
pos=[ov.index(x) for x in expected]
assert pos==sorted(pos),pos
assert ov.count('HermesCloudCard(s)')==1
assert ov.count('WorkloadIntelligenceCard(s)')==1

print('HERMESCLOUD_DISPLAY_FIX=PASS')
print('LITERAL_BACKSLASH_N=NONE')
print('CLOUD_FAILURE_REASON=VISIBLE')
print('OVERVIEW_ORDER_CHANGED=NO')
print('BACKEND_AUTHORITY_CHANGED=NO')
