package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.neurocomputer.neuromobile.data.model.WindowState

@Composable
fun WindowHost(
    window: WindowState,
    onSwipeUp: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val activeTab = window.tabs.find { it.id == window.activeTabId }
        ?: window.tabs.firstOrNull() ?: return

    Box(modifier.fillMaxSize()) {
        key(activeTab.id) {
            AppContent(tab = activeTab, modifier = Modifier.fillMaxSize())
        }
        ChevronHandle(
            onSwipeUp = onSwipeUp,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth(),
        )
    }
}
