package com.neurocomputer.neuromobile.ui.shell

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.TabType
import com.neurocomputer.neuromobile.data.model.WindowState
import com.neurocomputer.neuromobile.data.model.WindowTab

@Composable
fun NeuroOSShell(
    osViewModel: OsViewModel = hiltViewModel(),
    iconsViewModel: IconsViewModel = hiltViewModel(),
) {
    val osState by osViewModel.state.collectAsState()
    val iconsState by iconsViewModel.state.collectAsState()

    var switcherOpen by remember { mutableStateOf(false) }
    var pickerWindowId by remember { mutableStateOf<String?>(null) }

    val activeWindow = osState.windows.find { it.id == osState.activeWindowId }
    val isHome = activeWindow == null

    BackHandler(enabled = switcherOpen) { switcherOpen = false }
    BackHandler(enabled = pickerWindowId != null) { pickerWindowId = null }
    BackHandler(enabled = !isHome) { osViewModel.goHome() }

    Box(Modifier.fillMaxSize()) {
        if (isHome) {
            HomeScreen(
                iconOrder = iconsState.mobileOrder,
                onLaunch = { appId -> launchApp(appId, osViewModel) },
                modifier = Modifier.fillMaxSize(),
            )
            MobileDock(
                dockPins = iconsState.dockPins,
                onLaunch = { appId -> launchApp(appId, osViewModel) },
                modifier = Modifier.align(Alignment.BottomCenter),
            )
        } else {
            activeWindow?.let { win ->
                Column(Modifier.fillMaxSize()) {
                    MobileTabStrip(
                        window = win,
                        onTabClick = { tabId -> osViewModel.setActiveTab(win.id, tabId) },
                        onNewTab = { pickerWindowId = win.id },
                        onSwitcherOpen = { switcherOpen = true },
                    )
                    WindowHost(
                        window = win,
                        onSwipeUp = { switcherOpen = true },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }

        if (switcherOpen) {
            AppSwitcher(
                windows = osState.windows,
                activeWindowId = osState.activeWindowId,
                onFocus = { id -> osViewModel.focusWindow(id); switcherOpen = false },
                onClose = { id -> osViewModel.closeWindow(id) },
                onDismiss = { switcherOpen = false },
                onNewWindow = { switcherOpen = false; pickerWindowId = "__new__" },
            )
        }

        pickerWindowId?.let { winId ->
            AppPicker(
                onPick = { appId ->
                    pickerWindowId = null
                    if (winId == "__new__") {
                        launchApp(appId, osViewModel)
                    } else {
                        addTabToExistingWindow(appId, winId, osViewModel)
                    }
                },
                onDismiss = { pickerWindowId = null },
            )
        }
    }
}

private fun launchApp(appId: com.neurocomputer.neuromobile.data.model.AppId, osViewModel: OsViewModel) {
    val app = APP_MAP[appId] ?: return
    val cid = "${appId.name.lowercase()}-${System.currentTimeMillis()}"
    val tab = WindowTab(
        id = "tab-$cid", cid = cid,
        appId = appId, title = app.name, type = app.tabType,
    )
    osViewModel.openWindow(
        WindowState(
            id = "w-$cid", zIndex = 0, minimized = false,
            tabs = listOf(tab), activeTabId = tab.id,
        )
    )
}

private fun addTabToExistingWindow(
    appId: com.neurocomputer.neuromobile.data.model.AppId,
    windowId: String,
    osViewModel: OsViewModel,
) {
    val app = APP_MAP[appId] ?: return
    val cid = "${appId.name.lowercase()}-${System.currentTimeMillis()}"
    val tab = WindowTab(
        id = "tab-$cid", cid = cid,
        appId = appId, title = app.name, type = app.tabType,
    )
    osViewModel.addTabToWindow(windowId, tab, makeActive = true)
}
