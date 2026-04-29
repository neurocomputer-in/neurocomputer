package com.neurocomputer.neuromobile.data

import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.data.model.TabType
import org.junit.Assert.*
import org.junit.Test

class AppRegistryTest {
    @Test fun `APP_LIST has 18 apps`() = assertEquals(18, APP_LIST.size)

    @Test fun `APP_MAP lookup by id works`() {
        val app = APP_MAP[AppId.NEURO]!!
        assertEquals("Neuro", app.name)
        assertEquals(TabType.CHAT, app.tabType)
        assertTrue(app.pinned)
    }

    @Test fun `pinned apps are 8`() = assertEquals(8, APP_LIST.count { it.pinned })

    @Test fun `desktop app has DESKTOP tabType`() =
        assertEquals(TabType.DESKTOP, APP_MAP[AppId.NEURODESKTOP]!!.tabType)

    @Test fun `terminal app has no agentType`() =
        assertNull(APP_MAP[AppId.TERMINAL]!!.agentType)

    @Test fun `APP_MAP has same size as APP_LIST`() =
        assertEquals(APP_LIST.size, APP_MAP.size)
}
