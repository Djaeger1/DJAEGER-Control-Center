package com.djaeger.controlcenter

import kotlin.math.abs

internal data class PowerObservation(
    val currentUa: Long = -1,
    val voltageUv: Long = -1,
    val powerMw: Double = -1.0,
    val valid: String = "REJECTED",
    val reason: String = "NO_SAMPLE",
)

internal object TelemetryNormalizer {
    private const val MIN_VOLTAGE_UV = 2_500_000L
    private const val MAX_VOLTAGE_UV = 5_000_000L
    private const val MIN_POWER_MW = 100.0
    private const val MAX_POWER_MW = 15_000.0

    private data class CurrentCandidate(
        val currentUa: Long,
        val powerMw: Double,
        val source: String,
        val scale: String,
    )

    fun normalizeThermal(raw: Double?): Int {
        if (raw == null || !raw.isFinite()) return -1
        val celsius = if (abs(raw) > 1000.0) raw / 1000.0 else raw
        return celsius.takeIf { it in 0.0..150.0 }?.toInt() ?: -1
    }

    fun normalizeBatteryTemp(raw: Double?): Int {
        if (raw == null || !raw.isFinite()) return -1
        val celsius = when {
            abs(raw) > 1000.0 -> raw / 1000.0
            abs(raw) > 100.0 -> raw / 10.0
            else -> raw
        }
        return celsius.takeIf { it in 0.0..100.0 }?.toInt() ?: -1
    }

    fun maxThermal(
        thermals: List<Pair<String, Double>>,
        matcher: (String) -> Boolean,
    ): Int = thermals.asSequence()
        .filter { matcher(it.first) }
        .map { normalizeThermal(it.second) }
        .filter { it >= 0 }
        .maxOrNull() ?: -1

    fun observePower(
        standardRaw: Long?,
        sm5602Raw: Long?,
        voltageRaw: Long?,
        status: String?,
    ): PowerObservation {
        val voltageUv = voltageRaw?.takeIf { it > 0 } ?: -1
        if (voltageUv !in MIN_VOLTAGE_UV..MAX_VOLTAGE_UV) {
            return PowerObservation(
                voltageUv = voltageUv,
                reason = if (voltageUv < 0) "NO_VOLTAGE" else "VOLTAGE_IMPLAUSIBLE",
            )
        }

        // The standard battery node is authoritative. SM5602 is used only when
        // that node is missing or cannot be normalized to a plausible sample.
        val candidate = currentCandidate(standardRaw, voltageUv, "BATTERY_CURRENT")
            ?: currentCandidate(sm5602Raw, voltageUv, "SM5602_FALLBACK")
            ?: return PowerObservation(
                voltageUv = voltageUv,
                reason = "CURRENT_MISSING_OR_IMPLAUSIBLE",
            )

        val normalizedStatus = status?.trim().orEmpty().ifBlank { "NA" }
        val isDischarging = normalizedStatus.equals("Discharging", ignoreCase = true)
        return PowerObservation(
            currentUa = candidate.currentUa,
            voltageUv = voltageUv,
            powerMw = candidate.powerMw,
            valid = if (isDischarging) "VALID" else "REJECTED",
            reason = if (isDischarging) {
                "OK_${candidate.source}_${candidate.scale}"
            } else {
                "STATUS_${normalizedStatus}_${candidate.source}_${candidate.scale}"
            },
        )
    }

    private fun currentCandidate(
        raw: Long?,
        voltageUv: Long,
        source: String,
    ): CurrentCandidate? {
        if (raw == null || raw == Long.MIN_VALUE || raw == 0L) return null
        val absoluteRaw = abs(raw)

        val nativePower = powerMw(absoluteRaw, voltageUv)
        if (nativePower in MIN_POWER_MW..MAX_POWER_MW) {
            return CurrentCandidate(absoluteRaw, nativePower, source, "UA_NATIVE")
        }

        // Mirrors the module's vendor-kernel normalization: a plausible mA
        // value (for example 589) is promoted to uA and validated again.
        if (absoluteRaw in 20L..5000L) {
            val convertedUa = absoluteRaw * 1000L
            val convertedPower = powerMw(convertedUa, voltageUv)
            if (convertedPower in MIN_POWER_MW..MAX_POWER_MW) {
                return CurrentCandidate(convertedUa, convertedPower, source, "MA_X1000")
            }
        }
        return null
    }

    private fun powerMw(currentUa: Long, voltageUv: Long): Double =
        currentUa.toDouble() * voltageUv.toDouble() / 1_000_000_000.0
}
