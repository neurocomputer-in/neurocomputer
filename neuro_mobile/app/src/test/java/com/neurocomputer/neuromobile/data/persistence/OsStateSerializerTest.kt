package com.neurocomputer.neuromobile.data.persistence

import com.neurocomputer.neuromobile.data.model.*
import org.junit.Assert.*
import org.junit.Test

class OsStateSerializerTest {

    private fun makeTab(cid: String) = WindowTab(
        id = "tab-$cid", cid = cid,
        appId = AppId.NEURO, title = "Neuro", type = TabType.CHAT,
    )

    private fun makeWindow(id: String, cid: String) = WindowState(
        id = id, zIndex = 1, minimized = false,
        tabs = listOf(makeTab(cid)), activeTabId = "tab-$cid",
    )

    @Test fun `OsState roundtrips through JSON`() {
        val original = PersistedOsState(
            windows = listOf(makeWindow("w-1", "conv-abc")),
            activeWindowId = "w-1",
        )
        val json = original.toJson()
        val restored = json.toPersistedOsState()
        assertEquals(original, restored)
    }

    @Test fun `empty OsState roundtrips`() {
        val original = PersistedOsState(windows = emptyList(), activeWindowId = null)
        assertEquals(original, original.toJson().toPersistedOsState())
    }

    @Test fun `IconsState roundtrips`() {
        val original = PersistedIconsState(
            mobileOrder = listOf("NEURO", "TERMINAL", "IDE"),
            dockPins = listOf("NEURO", "TERMINAL"),
        )
        assertEquals(original, original.toJson().toPersistedIconsState())
    }
}
