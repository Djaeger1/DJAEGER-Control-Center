package com.djaeger.controlcenter

import android.content.Context

/**
 * App-local delivery gate. The control-plane reports facts/events; Android owns delivery.
 * No module state, hardware state, API key, or network configuration is written here.
 */
class BugNotificationGate(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        "djaeger_bug_notification_state",
        Context.MODE_PRIVATE
    )

    data class Candidate(
        val eventId: String,
        val severity: String,
        val code: String,
        val component: String,
        val summary: String
    )

    fun candidate(state: BugHealthState): Candidate? {
        if (!state.notificationEligible) return null
        val id = state.eventId.trim()
        if (id.isBlank()) return null
        if (prefs.getString(KEY_LAST_DELIVERED_EVENT, "") == id) return null
        return Candidate(
            eventId = id,
            severity = state.severity.uppercase(),
            code = state.code.take(120),
            component = state.component.take(120),
            summary = state.summary.take(500)
        )
    }

    /** Call only after NotificationManager accepted the notification request. */
    fun markDelivered(eventId: String) {
        val id = eventId.trim()
        if (id.isBlank()) return
        prefs.edit()
            .putString(KEY_LAST_DELIVERED_EVENT, id.take(512))
            .putLong(KEY_LAST_DELIVERED_AT, System.currentTimeMillis())
            .apply()
    }

    fun lastDeliveredEventId(): String = prefs.getString(KEY_LAST_DELIVERED_EVENT, "").orEmpty()

    companion object {
        private const val KEY_LAST_DELIVERED_EVENT = "last_delivered_event_id"
        private const val KEY_LAST_DELIVERED_AT = "last_delivered_at_ms"
    }
}
