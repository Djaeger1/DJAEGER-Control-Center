package com.djaeger.controlcenter

import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * The only recurring root read intended for UI polling.
 * Reads the one Observer-owned cc_snapshot; never scans sysfs.
 */
class ConsolidatedSnapshotReader(
    private val snapshotPath: String = "/data/adb/djaeger_observer/cc_snapshot"
) {
    data class Result(
        val ok: Boolean,
        val raw: String = "",
        val sections: Map<String, String> = emptyMap(),
        val bugHealth: BugHealthState = BugHealthState(),
        val error: String = ""
    )

    fun read(timeoutMs: Long = 4000): Result {
        val executor = Executors.newSingleThreadExecutor()
        return try {
            // Fixed command and fixed path: no user-controlled shell interpolation.
            val command = "cat '$snapshotPath' 2>/dev/null"
            val process = ProcessBuilder("su", "-c", command)
                .redirectErrorStream(true)
                .start()
            val future = executor.submit<String> {
                process.inputStream.bufferedReader().use { it.readText() }
            }
            if (!process.waitFor(timeoutMs, TimeUnit.MILLISECONDS)) {
                process.destroy()
                if (process.isAlive) process.destroyForcibly()
                future.cancel(true)
                Result(false, error = "SNAPSHOT_TIMEOUT")
            } else {
                val raw = try { future.get(300, TimeUnit.MILLISECONDS) } catch (_: Exception) { "" }
                if (process.exitValue() != 0 || raw.isBlank()) {
                    Result(false, error = "SNAPSHOT_UNAVAILABLE")
                } else {
                    val sections = AtomicSnapshot.sections(raw)
                    if (sections.isEmpty()) {
                        Result(false, raw = raw, error = "SNAPSHOT_MALFORMED")
                    } else {
                        val bug = BugHealthParser.parse(
                            sections["BUG_HEALTH"].orEmpty(),
                            sections["BUG_EVENTS"].orEmpty()
                        )
                        Result(true, raw = raw, sections = sections, bugHealth = bug)
                    }
                }
            }
        } catch (e: Exception) {
            Result(false, error = "SNAPSHOT_ERROR=" + (e.message ?: "unknown"))
        } finally {
            executor.shutdownNow()
        }
    }
}
