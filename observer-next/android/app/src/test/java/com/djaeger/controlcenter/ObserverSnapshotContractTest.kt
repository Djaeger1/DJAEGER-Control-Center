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
            0.2.1-observer-next
            __RUNTIME__
            UPDATED_AT=1789970000
            ACTIVE=1
            GAME=sts.al
            WINDOW_MODE=FOREGROUND
            USER_MODE=OBSERVER
            __TEL__
            1789970000,54,50,39,37,1000000,1800000,600000000,STOCK_OBSERVER,16.67,60.0,1.0,17.0,20.0,0,Discharging,500000,4200000,2100,VALID,MEASURED_DISCHARGE,sts.al,FOREGROUND
            __CONTROL_CENTER_SYNC__
            CONTRACT=OBSERVER_NEXT_V1
            MODULE_VERSION_CODE=201
            CONTROL_CENTER_VERSION_CODE=102
            __AUTHORITY__
            STATE=READ_ONLY
            SYSFS_WRITES=DISABLED
            EXECUTOR=NOT_STARTED
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
        assertEquals("0.2.1-observer-next", mapped.moduleVersion)
        assertEquals("sts.al", mapped.runtime["GAME"])
        assertEquals("OBSERVER_NEXT_V1", AtomicSnapshot.keyValues(mapped.controlCenterSync)["CONTRACT"])
        assertEquals("DISABLED", AtomicSnapshot.keyValues(mapped.authority)["SYSFS_WRITES"])
        assertEquals("NOT_STARTED", AtomicSnapshot.keyValues(mapped.authority)["EXECUTOR"])
    }
}
