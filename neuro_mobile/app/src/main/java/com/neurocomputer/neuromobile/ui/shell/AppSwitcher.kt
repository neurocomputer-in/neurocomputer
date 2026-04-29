package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.model.WindowState

@Composable
fun AppSwitcher(
    windows: List<WindowState>,
    activeWindowId: String?,
    onFocus: (String) -> Unit,
    onClose: (String) -> Unit,
    onDismiss: () -> Unit,
    onNewWindow: () -> Unit,
) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Color(0xCC000000))
            .clickable { onDismiss() },
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(windows, key = { it.id }) { win ->
                val activeTab = win.tabs.find { it.id == win.activeTabId }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(80.dp)
                        .background(
                            if (win.id == activeWindowId) Color(0xFF2d2d4a) else Color(0xFF1a1a2a),
                            RoundedCornerShape(12.dp),
                        )
                        .clickable { onFocus(win.id) }
                        .padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Column {
                        Text(
                            activeTab?.title ?: "Window",
                            color = Color.White,
                            fontSize = 14.sp,
                        )
                        Text(
                            "${win.tabs.size} tab${if (win.tabs.size != 1) "s" else ""}",
                            color = Color(0xFF9090a0),
                            fontSize = 12.sp,
                        )
                    }
                    Text(
                        "✕",
                        color = Color(0xFF9090a0),
                        fontSize = 16.sp,
                        modifier = Modifier
                            .clickable(onClick = { onClose(win.id) })
                            .padding(8.dp),
                    )
                }
            }
            item {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .background(Color(0xFF1a1a2a), RoundedCornerShape(12.dp))
                        .clickable { onNewWindow() },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("+ New Window", color = Color(0xFF9090a0))
                }
            }
        }
    }
}
