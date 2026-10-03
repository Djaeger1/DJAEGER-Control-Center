package com.djaeger.controlcenter

/**
 * Read-only representation of DJAEGER control-plane self diagnostics.
 * The Android app never promotes monitor heuristics to official bug state.
 */
data class BugHealthState(
    val health: String = "UNKNOWN",
    val openBug: Boolean = false,
    val eventId: String = "",
    val severity: String = "INFO",
    val component: String = "",
    val code: String = "",
    val summary: String = "",
    val facts: String = "",
    val hypothesis: String = "",
    val action: String = "",
    val recovery: String = "",
    val decisionId: String = "",
    val transactionId: String = "",
    val notifyPending: Boolean = false,
    val updatedAt: Long = 0L,
    val recentEvents: String = ""
) {
    val notificationEligible: Boolean
        get() = openBug && eventId.isNotBlank() && when (severity.uppercase()) {
            "CRITICAL", "HIGH" -> true
            "WARNING" -> notifyPending
            else -> false
        }
}

object BugHealthParser {
    private fun clean(value: String?): String {
        val x = value?.trim().orEmpty()
        return if (x.length >= 2 && ((x.first() == '\'' && x.last() == '\'') || (x.first() == '"' && x.last() == '"'))) {
            x.substring(1, x.length - 1)
        } else x
    }

    private fun bool(value: String?): Boolean = when (clean(value).uppercase()) {
        "1", "YES", "TRUE", "OPEN", "PENDING" -> true
        else -> false
    }

    fun parse(healthRaw: String, eventsRaw: String): BugHealthState {
        val kv = healthRaw.lineSequence().mapNotNull { line ->
            val p = line.indexOf('=')
            if (p <= 0) null else line.substring(0, p).trim().uppercase() to clean(line.substring(p + 1))
        }.toMap()

        fun get(vararg names: String): String {
            for (name in names) kv[name.uppercase()]?.takeIf { it.isNotBlank() }?.let { return it }
            return ""
        }

        val health = get("HEALTH", "BUG_HEALTH", "STATE").ifBlank {
            if (bool(get("OPEN_BUG"))) "DEGRADED" else "UNKNOWN"
        }
        val open = bool(get("OPEN_BUG", "BUG_OPEN")) || health.equals("OPEN", true)
        val severity = get("SEVERITY").ifBlank { "INFO" }.uppercase()

        return BugHealthState(
            health = health.uppercase(),
            openBug = open,
            eventId = get("EVENT_ID", "BUG_EVENT_ID"),
            severity = severity,
            component = get("COMPONENT"),
            code = get("CODE", "BUG_CODE"),
            summary = get("SUMMARY", "SYMPTOM"),
            facts = get("FACTS", "OBSERVED_FACTS"),
            hypothesis = get("HYPOTHESIS", "CAUSE_HYPOTHESIS"),
            action = get("ACTION", "AUTO_ACTION"),
            recovery = get("RECOVERY", "RECOVERY_STATE"),
            decisionId = get("DECISION_ID"),
            transactionId = get("TRANSACTION_ID"),
            notifyPending = bool(get("NOTIFY_PENDING", "NOTIFY_RECOMMENDED")),
            updatedAt = get("UPDATED_AT", "EVENT_AT").toLongOrNull() ?: 0L,
            recentEvents = eventsRaw.trim()
        )
    }

    /**
     * Build a bounded diagnostic report suitable for the clipboard.
     * Raw key vault/config/token material is deliberately not accepted by this API.
     */
    fun diagnosticReport(state: BugHealthState): String = buildString {
        appendLine("DJAEGER BUG & HEALTH")
        appendLine("Health=${state.health}")
        appendLine("Open=${state.openBug}")
        appendLine("Severity=${state.severity}")
        appendLine("Component=${state.component.ifBlank { "—" }}")
        appendLine("Code=${state.code.ifBlank { "—" }}")
        appendLine("EventID=${state.eventId.ifBlank { "—" }}")
        appendLine("DecisionID=${state.decisionId.ifBlank { "—" }}")
        appendLine("TransactionID=${state.transactionId.ifBlank { "—" }}")
        appendLine("Summary=${state.summary.ifBlank { "—" }}")
        appendLine("Facts=${state.facts.ifBlank { "—" }}")
        appendLine("Hypothesis=${state.hypothesis.ifBlank { "—" }}")
        appendLine("Action=${state.action.ifBlank { "—" }}")
        appendLine("Recovery=${state.recovery.ifBlank { "—" }}")
        appendLine("UpdatedAt=${state.updatedAt}")
        if (state.recentEvents.isNotBlank()) {
            appendLine("RecentEvents:")
            append(state.recentEvents.lineSequence().takeLastBounded(20).joinToString("\n"))
        }
    }.take(16_000)

    private fun Sequence<String>.takeLastBounded(max: Int): List<String> {
        val q = ArrayDeque<String>()
        for (line in this) {
            if (q.size == max) q.removeFirst()
            q.addLast(line.take(1000))
        }
        return q.toList()
    }
}
