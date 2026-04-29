package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.neurocomputer.neuromobile.data.model.TabType
import com.neurocomputer.neuromobile.data.model.WindowTab
import com.neurocomputer.neuromobile.ui.apps.chat.ChatApp
import com.neurocomputer.neuromobile.ui.apps.desktop.DesktopApp
import com.neurocomputer.neuromobile.ui.apps.ide.IDEApp
import com.neurocomputer.neuromobile.ui.apps.terminal.TerminalApp

@Composable
fun AppContent(tab: WindowTab, modifier: Modifier = Modifier) {
    when (tab.type) {
        TabType.CHAT     -> ChatApp(
            cid = tab.cid,
            agentId = tab.appId.name.lowercase(),
            modifier = modifier,
        )
        TabType.TERMINAL -> TerminalApp(cid = tab.cid, modifier = modifier)
        TabType.IDE      -> IDEApp(cid = tab.cid, modifier = modifier)
        TabType.DESKTOP  -> DesktopApp(modifier = modifier)
    }
}

@Composable
private fun PlaceholderScreen(label: String, bg: Color, modifier: Modifier) {
    Box(modifier.fillMaxSize().background(bg), contentAlignment = Alignment.Center) {
        Text(label, color = Color.White)
    }
}
