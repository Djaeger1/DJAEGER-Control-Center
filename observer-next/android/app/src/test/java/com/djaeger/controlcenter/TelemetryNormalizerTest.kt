package com.djaeger.controlcenter

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TelemetryNormalizerTest {
    @Test
    fun standardBatteryCurrentHasPriorityOverSm5602() {
        val observed = TelemetryNormalizer.observePower(
            standardRaw = -400_000,
            sm5602Raw = 589,
            voltageRaw = 4_247_000,
            status = "Discharging",
        )

        assertEquals(400_000, observed.currentUa)
        assertEquals("VALID", observed.valid)
        assertTrue(observed.reason.contains("BATTERY_CURRENT_UA_NATIVE"))
    }

    @Test
    fun sm5602IsFallbackAndVendorMilliampValueIsNormalized() {
        val observed = TelemetryNormalizer.observePower(
            standardRaw = null,
            sm5602Raw = 589,
            voltageRaw = 4_247_000,
            status = "Discharging",
        )

        assertEquals(589_000, observed.currentUa)
        assertTrue(observed.powerMw in 2_499.0..2_503.0)
        assertEquals("VALID", observed.valid)
        assertTrue(observed.reason.contains("SM5602_FALLBACK_MA_X1000"))
    }

    @Test
    fun chargingSampleIsNeverMarkedValidDischargePower() {
        val observed = TelemetryNormalizer.observePower(
            standardRaw = 589_000,
            sm5602Raw = null,
            voltageRaw = 4_247_000,
            status = "Charging",
        )

        assertEquals("REJECTED", observed.valid)
        assertTrue(observed.reason.startsWith("STATUS_Charging_"))
    }

    @Test
    fun implausibleVoltageIsRejected() {
        val observed = TelemetryNormalizer.observePower(
            standardRaw = 589_000,
            sm5602Raw = null,
            voltageRaw = 8_000_000,
            status = "Discharging",
        )

        assertEquals(-1, observed.currentUa)
        assertEquals(-1.0, observed.powerMw)
        assertEquals("VOLTAGE_IMPLAUSIBLE", observed.reason)
    }

    @Test
    fun missingThermalsRemainMissing() {
        val thermals = listOf("xo-therm" to 43_000.0)
        val cpu = TelemetryNormalizer.maxThermal(thermals) { it.startsWith("cpu-") }

        assertEquals(-1, cpu)
        assertEquals(-1, TelemetryNormalizer.normalizeBatteryTemp(null))
    }

    @Test
    fun thermalUnitsAreNormalized() {
        assertEquals(55, TelemetryNormalizer.normalizeThermal(55_300.0))
        assertEquals(41, TelemetryNormalizer.normalizeBatteryTemp(414.0))
        assertEquals(41, TelemetryNormalizer.normalizeBatteryTemp(41_400.0))
    }
}
