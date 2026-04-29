package com.neurocomputer.neuromobile.ui.shell

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.TabType
import com.neurocomputer.neuromobile.data.model.WindowState
import com.neurocomputer.neuromobile.data.model.WindowTab
import com.neurocomputer.neuromobile.ui.apps.desktop.MobileDesktopViewModel

@Composable
fun NeuroOSShell(
    osViewModel: OsViewModel = hiltViewModel(),
    iconsViewModel: IconsViewModel = hiltViewModel(),
    desktopViewModel: MobileDesktopViewModel = hiltViewModel(),
) {
    val osState by osViewModel.state.collectAsState()
    val wsConnected by osViewModel.wsConnected.collectAsState()
    val iconsState by iconsViewModel.state.collectAsState()
    val desktopState by desktopViewModel.state.collectAsState()
    val kioskActive = desktopState.kioskActive

    var switcherOpen by remember { mutableStateOf(false) }
    var pickerWindowId by remember { mutableStateOf<String?>(null) }
    var controlSheetOpen by remember { mutableStateOf(false) }

    val activeWindow = osState.windows.find { it.id == osState.activeWindowId }
    val isHome = activeWindow == null

    BackHandler(enabled = controlSheetOpen) { controlSheetOpen = false }
    BackHandler(enabled = switcherOpen) { switcherOpen = false }
    BackHandler(enabled = pickerWindowId != null) { pickerWindowId = null }
    BackHandler(enabled = !isHome) { osViewModel.goHome() }

    Box(Modifier.fillMaxSize()) {
        if (isHome) {
            // Same chrome as in-window (status-bar inset + 36dp top strip with
            // hamburger). Keeps the menu affordance in a consistent location
            // whether the user is on home or inside a window.
            Column(
                Modifier
                    .fillMaxSize()
                    .windowInsetsPadding(WindowInsets.statusBars)
            ) {
                MobileTabStrip(
                    window = null,
                    onTabClick = { },
                    onNewTab = { pickerWindowId = "__new__" },
                    onSwitcherOpen = { switcherOpen = true },
                    onMenuOpen = { controlSheetOpen = true },
                )
                HomeScreen(
                    iconOrder = iconsState.mobileOrder,
                    onLaunch = { appId -> launchApp(appId, osViewModel) },
                    modifier = Modifier.weight(1f),
                )
            }
            MobileDock(
                dockPins = iconsState.dockPins,
                onLaunch = { appId -> launchApp(appId, osViewModel) },
                onOpenLauncher = { pickerWindowId = "__new__" },
                modifier = Modifier.align(Alignment.BottomCenter),
            )
        } else {
            activeWindow?.let { win ->
                // Push the tab strip below the system status bar — without this
                // padding edge-to-edge mode draws the 36dp strip under the
                // notch/clock area and it disappears.
                Column(
                    Modifier
                        .fillMaxSize()
                        .windowInsetsPadding(WindowInsets.statusBars)
                ) {
                    if (!kioskActive) {
                        MobileTabStrip(
                            window = win,
                            onTabClick = { tabId -> osViewModel.setActiveTab(win.id, tabId) },
                            onNewTab = { pickerWindowId = win.id },
                            onSwitcherOpen = { switcherOpen = true },
                            onMenuOpen = { controlSheetOpen = true },
                        )
                    }
                    WindowHost(
                        window = win,
                        onSwipeUp = { switcherOpen = true },
                        modifier = Modifier.weight(1f),
                        showChevron = !kioskActive,
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
                onLaunchApp = { appId ->
                    switcherOpen = false
                    launchApp(appId, osViewModel)
                },
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

        if (controlSheetOpen) {
            MobileControlSheet(
                wsConnected = wsConnected,
                workspaces = osState.workspaces,
                currentWorkspaceId = osState.currentWorkspaceId,
                projects = osState.projects,
                currentProjectId = osState.currentProjectId,
                windows = osState.windows,
                activeWindowId = osState.activeWindowId,
                onFocusWindow = { id ->
                    controlSheetOpen = false
                    osViewModel.focusWindow(id)
                },
                onSelectWorkspace = osViewModel::selectWorkspace,
                onSelectProject = osViewModel::selectProject,
                onOpenAppSwitcher = {
                    controlSheetOpen = false
                    switcherOpen = true
                },
                onGoHome = {
                    controlSheetOpen = false
                    osViewModel.goHome()
                },
                onDismiss = { controlSheetOpen = false },
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
