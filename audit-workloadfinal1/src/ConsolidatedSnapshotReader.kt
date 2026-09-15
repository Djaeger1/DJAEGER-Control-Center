package com.djaeger.controlcenter

import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * The only recurring root read intended for UI polling.
 * Reads cc_snapshot plus DJAEGER-owned atomic workload state in the same root process; never scans sysfs.
 */
class ConsolidatedSnapshotReader(
    private val snapshotPath: String = "/data/adb/djaeger_ai/cc_snapshot"
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
            val command = """
                cat '$snapshotPath' 2>/dev/null
                printf '\n__WORKLOAD_CONTEXT__\n'
                cat /data/adb/djaeger_ai/workload_context.env 2>/dev/null
                printf '\n__WORKLOAD_GATE__\n'
                cat /data/adb/djaeger_ai/workload_gate_state.env 2>/dev/null
                printf '\n__PROPOSAL_BINDING__\n'
                cat /data/adb/djaeger_ai/proposal_binding_state.env 2>/dev/null
                printf '\n__WORKLOAD_FINAL__\n'
                cat /data/adb/djaeger_ai/workload_final_state.env 2>/dev/null
                printf '\n__WORKLOAD_EXEC_GUARD__\n'
                cat /data/adb/djaeger_ai/workload_exec_guard_state.env 2>/dev/null
                printf '\n__APP_REGISTRY__\n'
                cat /data/adb/djaeger_ai/workload/app_registry.tsv 2>/dev/null
                printf '\n__GAME_REGISTRY_MANUAL__\n'
                cat /data/adb/djaeger_ai/custom_games.tsv 2>/dev/null
                printf '\n__CONTROL_CENTER_SYNC__\n'
                printf "CONTRACT='REBUILD3_LANG3_MWFIX2_ATTR1_MATH1_HK1_SYSFS1_CCSYNC1_GAMEREG1_SHAREDINT1_HERMESCLOUD1_WORKLOADFINAL1'\n"
                printf "MODULE_VERSION_CODE='129637'\n"
                printf "CONTROL_CENTER_VERSION_CODE='12261'\n"
                printf "WORKLOAD_FINAL='WORKLOADFINAL1'\n"
                printf "WORKLOAD_CLASSIFICATION='GAME_APP_SYSTEM'\n"
                printf "DUAL_REGISTRY='ENFORCED'\n"
                printf "PREEXEC_WORKLOAD_GUARD='ACTIVE'\n"
                printf "WORKLOAD_DATA_SOURCE='SINGLE_ROOT_READ_DJAEGER_STATE'\n"
            """.trimIndent()
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
