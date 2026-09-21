package com.djaeger.controlcenter

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class ObserverSnapshotContractTest {
    @Test
    fun observerContractMapsFromOneAtomicSnapshot() {
        val raw = """
            __INSTALLED__
            1
            __VERSION__
            1.0.0-adaptive-clean
            __RUNTIME__
            UPDATED_AT=1789970000
            ACTIVE=1
            GAME=sts.al
            WINDOW_MODE=FOREGROUND
            USER_MODE=AUTO
            __TEL__
            1789970000,54,50,39,37,1000000,1800000,600000000,ADAPTIVE_LEARNED,16.67,60.0,1.0,17.0,20.0,0,Discharging,500000,4200000,2100,VALID,MEASURED_DISCHARGE,sts.al,FOREGROUND
            __CONTROL_CENTER_SYNC__
            CONTRACT=DJAEGER_AI_ADAPTIVE_V1
            MODULE_VERSION_CODE=202
            CONTROL_CENTER_VERSION_CODE=103
            __AUTHORITY__
            STATE=LOCAL_GATED
            SYSFS_WRITES=EXECUTOR_ONLY
            EXECUTOR=APPLIED
            __BUG_HEALTH__
            STATE=OK
        """.trimIndent()

        val sections = AtomicSnapshot.sections(raw)
        val mapped = assertNotNull(ConsolidatedRuntimeMapper.map(
            ConsolidatedSnapshotReader.Result(
                ok = true,
                raw = raw,
                sections = sections,
                bugHealth = BugHealthParser.parse(sections["BUG_HEALTH"].orEmpty(), ""),
            )
        ))

        assertTrue(mapped.installed)
        assertEquals("1.0.0-adaptive-clean", mapped.moduleVersion)
        assertEquals("sts.al", mapped.runtime["GAME"])
        assertEquals("DJAEGER_AI_ADAPTIVE_V1", AtomicSnapshot.keyValues(mapped.controlCenterSync)["CONTRACT"])
        assertEquals("EXECUTOR_ONLY", AtomicSnapshot.keyValues(mapped.authority)["SYSFS_WRITES"])
        assertEquals("APPLIED", AtomicSnapshot.keyValues(mapped.authority)["EXECUTOR"])
    }
}
