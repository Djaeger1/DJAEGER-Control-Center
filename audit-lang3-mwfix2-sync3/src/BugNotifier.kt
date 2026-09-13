package com.djaeger.controlcenter

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build

/** Android delivery only. DJAEGER control-plane remains the source of bug truth. */
class BugNotifier(private val context: Context) {
    private val manager = context.getSystemService(NotificationManager::class.java)
    private val gate = BugNotificationGate(context)

    fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "DJAEGER Bug & Health",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Verified DJAEGER self-diagnostic events"
            enableVibration(true)
        }
        manager.createNotificationChannel(channel)
    }

    /** Returns true only when a new eligible event was submitted to Android. */
    fun notifyIfNeeded(state: BugHealthState): Boolean {
        val candidate = gate.candidate(state) ?: return false
        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return false

        ensureChannel()
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("open_bug_health", true)
            putExtra("bug_event_id", candidate.eventId)
        }
        val pending = PendingIntent.getActivity(
            context,
            candidate.eventId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val title = when (candidate.severity) {
            "CRITICAL" -> "DJAEGER • Critical bug detected"
            "HIGH" -> "DJAEGER • High severity bug"
            else -> "DJAEGER • Health warning"
        }
        val detail = listOf(candidate.component, candidate.code, candidate.summary)
            .filter { it.isNotBlank() }.joinToString(" • ").take(900)
        val notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            android.app.Notification.Builder(context, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION") android.app.Notification.Builder(context)
        }.setSmallIcon(android.R.drawable.stat_notify_error)
            .setContentTitle(title)
            .setContentText(detail.ifBlank { "Open Control Center for diagnostic details" })
            .setStyle(android.app.Notification.BigTextStyle().bigText(detail))
            .setContentIntent(pending)
            .setAutoCancel(true)
            .setOnlyAlertOnce(true)
            .setCategory(android.app.Notification.CATEGORY_ERROR)
            .build()

        return try {
            manager.notify(candidate.eventId.hashCode(), notification)
            gate.markDelivered(candidate.eventId)
            true
        } catch (_: SecurityException) {
            false
        }
    }

    companion object {
        const val CHANNEL_ID = "djaeger_bug_health_v1"
    }
}
