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
