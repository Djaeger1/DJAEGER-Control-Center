package com.djaeger.controlcenter

/**
 * Compatibility mapper used while r9 removes the legacy multi-read snapshot path.
 * It consumes only data already published by DJAEGER in cc_snapshot.
 */
object ConsolidatedRuntimeMapper {
    data class Mapped(
        val installed: Boolean,
        val moduleVersion: String,
        val runtime: Map<String, String>,
        val telemetryRaw: String,
        val brain: String,
        val thoughts: String,
        val memoryStatus: String,
        val authority: String,
        val sessionSafety: String,
        val supervisor: String,
        val hermesCtx1Status: String,
        val hermesCtx1Runtime: String,
        val hermesCtx1Safety: String,
        val hermesCtx1Hardware: String,
        val hermesCtx1Memory: String,
        val hermesCtx1Learning: String,
        val hermesCognitionStatus: String,
        val hermesMemoryVNext: String,
        val hermesReasoningV2: String,
        val hermesSkillsVNext: String,
        val hermesLearningV2: String,
        val hermesResearchV2: String,
        val hermesHumanComfort: String,
        val hermesLanguage: String,
        val hermesMath: String,
        val hermesKernel1: String,
        val agentSysfs1Capability: String,
        val agentSysfs1Execution: String,
        val controlCenterSync: String,
        val strategyResult: String,
        val envelope: String,
        val geminiHttp: String,
        val geminiServer: String,
        val decisions: String,
        val plans: String,
        val frameIntel: String,
        val log: String,
        val network: String,
        val reasoning: String,
        val resync: String,
        val execution: String,
        val policyContext: String,
        val attribution: String,
        val bugHealth: BugHealthState
    )

    fun map(result: ConsolidatedSnapshotReader.Result): Mapped? {
        if (!result.ok) return null
        val s = result.sections
        val installedText = s["INSTALLED"].orEmpty().trim()
        val installed = installedText == "1" || installedText.equals("YES", true) || installedText.equals("TRUE", true)
        val runtime = AtomicSnapshot.keyValues(s["RUNTIME"].orEmpty())
        return Mapped(
            installed = installed,
            moduleVersion = s["VERSION"].orEmpty().trim().ifBlank { "unknown" },
            runtime = runtime,
            telemetryRaw = s["TEL"].orEmpty().lineSequence().lastOrNull { it.isNotBlank() }.orEmpty(),
            brain = s["BRAIN"].orEmpty(),
            thoughts = s["THOUGHTS"].orEmpty(),
            memoryStatus = s["MEMORY"].orEmpty(),
            authority = s["AUTHORITY"].orEmpty(),
            sessionSafety = s["SESSION_SAFETY"].orEmpty(),
            supervisor = s["SUPERVISOR"].orEmpty(),
            hermesCtx1Status = s["HERMES_CTX1_STATUS"].orEmpty(),
            hermesCtx1Runtime = s["HERMES_CTX1_RUNTIME"].orEmpty(),
            hermesCtx1Safety = s["HERMES_CTX1_SAFETY"].orEmpty(),
            hermesCtx1Hardware = s["HERMES_CTX1_HARDWARE"].orEmpty(),
            hermesCtx1Memory = s["HERMES_CTX1_MEMORY"].orEmpty(),
            hermesCtx1Learning = s["HERMES_CTX1_LEARNING"].orEmpty(),
            hermesCognitionStatus = s["HERMES_COGNITION_STATUS"].orEmpty(),
            hermesMemoryVNext = s["HERMES_MEMORY_VNEXT"].orEmpty(),
            hermesReasoningV2 = s["HERMES_REASONING_V2"].orEmpty(),
            hermesSkillsVNext = s["HERMES_SKILLS_VNEXT"].orEmpty(),
            hermesLearningV2 = s["HERMES_LEARNING_V2"].orEmpty(),
            hermesResearchV2 = s["HERMES_RESEARCH_V2"].orEmpty(),
            hermesHumanComfort = s["HERMES_HUMAN_COMFORT"].orEmpty(),
            hermesLanguage = s["HERMES_LANGUAGE"].orEmpty(),
            hermesMath = s["HERMES_MATH"].orEmpty(),
            hermesKernel1 = s["HERMES_KERNEL1"].orEmpty(),
            agentSysfs1Capability = s["AGENT_SYSFS1_CAPABILITY"].orEmpty(),
            agentSysfs1Execution = s["AGENT_SYSFS1_EXECUTION"].orEmpty(),
            controlCenterSync = s["CONTROL_CENTER_SYNC"].orEmpty(),
            strategyResult = s["STRATEGY_RESULT"].orEmpty(),
            envelope = s["ENV"].orEmpty(),
            geminiHttp = s["HTTP"].orEmpty(),
            geminiServer = s["SERVER"].orEmpty(),
            decisions = s["DECISIONS"].orEmpty(),
            plans = s["PLANS"].orEmpty(),
            frameIntel = s["FRAME"].orEmpty(),
            log = s["LOG"].orEmpty(),
            network = s["NETWORK"].orEmpty(),
            reasoning = s["REASONING"].orEmpty(),
            resync = s["RESYNC"].orEmpty(),
            execution = s["EXECUTION"].orEmpty(),
            policyContext = s["POLICY_CONTEXT"].orEmpty(),
            attribution = s["ATTRIBUTION"].orEmpty(),
            bugHealth = result.bugHealth
        )
    }
}
