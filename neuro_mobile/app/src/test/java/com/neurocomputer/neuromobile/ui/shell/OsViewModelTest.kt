package com.neurocomputer.neuromobile.ui.shell

import com.neurocomputer.neuromobile.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class OsViewModelTest {

    private val dispatcher = UnconfinedTestDispatcher()

    @Before fun setUp() { Dispatchers.setMain(dispatcher) }
    @After fun tearDown() { Dispatchers.resetMain() }

    private fun makeTab(cid: String) = WindowTab(
        id = "tab-$cid", cid = cid,
        appId = AppId.NEURO, title = "Neuro", type = TabType.CHAT,
    )

    private fun makeWindow(id: String, cid: String) = WindowState(
        id = id, zIndex = 1, minimized = false,
        tabs = listOf(makeTab(cid)), activeTabId = "tab-$cid",
    )

    private fun vm() = testOsViewModel()

    @Test fun `openWindow adds window and sets activeWindowId`() {
        val vm = vm()
        vm.openWindow(makeWindow("w-1", "conv-1"))
        assertEquals("w-1", vm.state.value.activeWindowId)
        assertEquals(1, vm.state.value.windows.size)
    }

    @Test fun `closeWindow with last tab removes window and clears activeWindowId`() {
        val vm = vm()
        vm.openWindow(makeWindow("w-1", "conv-1"))
        vm.closeWindow("w-1")
        assertNull(vm.state.value.activeWindowId)
        assertTrue(vm.state.value.windows.isEmpty())
    }

    @Test fun `addTabToWindow appends tab and makes it active`() {
        val vm = vm()
        vm.openWindow(makeWindow("w-1", "conv-1"))
        val tab2 = makeTab("conv-2").copy(id = "tab-conv-2")
        vm.addTabToWindow("w-1", tab2, makeActive = true)
        val win = vm.state.value.windows.first()
        assertEquals(2, win.tabs.size)
        assertEquals("tab-conv-2", win.activeTabId)
    }

    @Test fun `closeTab with last tab closes window`() {
        val vm = vm()
        vm.openWindow(makeWindow("w-1", "conv-1"))
        vm.closeTab("w-1", "tab-conv-1")
        assertTrue(vm.state.value.windows.isEmpty())
    }

    @Test fun `setActiveTab updates activeTabId`() {
        val vm = vm()
        val tab2 = makeTab("conv-2").copy(id = "tab-conv-2")
        val win = makeWindow("w-1", "conv-1").copy(
            tabs = listOf(makeTab("conv-1"), tab2)
        )
        vm.openWindow(win)
        vm.setActiveTab("w-1", "tab-conv-2")
        assertEquals("tab-conv-2", vm.state.value.windows.first().activeTabId)
    }

    @Test fun `focusWindow sets activeWindowId`() {
        val vm = vm()
        vm.openWindow(makeWindow("w-1", "conv-1"))
        vm.openWindow(makeWindow("w-2", "conv-2"))
        vm.focusWindow("w-1")
        assertEquals("w-1", vm.state.value.activeWindowId)
    }

    @Test fun `closeTab picks adjacent tab not last tab`() {
        val vm = vm()
        val tabA = makeTab("a").copy(id = "tab-a")
        val tabB = makeTab("b").copy(id = "tab-b")
        val tabC = makeTab("c").copy(id = "tab-c")
        val win = WindowState(
            id = "w-1", zIndex = 1, minimized = false,
            tabs = listOf(tabA, tabB, tabC), activeTabId = "tab-b",
        )
        vm.openWindow(win)
        vm.closeTab("w-1", "tab-b")  // close middle tab while it's active
        val remaining = vm.state.value.windows.first()
        // Should pick tabC (index 1 in remaining [tabA, tabC]) not tabA (last would be tabC which is also correct here)
        // But if we close tabC (last), it should pick tabB (now last = index 1)
        assertEquals(2, remaining.tabs.size)
        assertEquals("tab-c", remaining.activeTabId)  // index 1 in [tabA, tabC] = tabC
    }
}
