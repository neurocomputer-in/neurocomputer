package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.model.WindowState
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

@Composable
fun MobileTabStrip(
    window: WindowState?,
    onTabClick: (tabId: String) -> Unit,
    onNewTab: () -> Unit,
    onSwitcherOpen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(36.dp)
            .background(NeuroColors.BackgroundDark)
            .windowInsetsPadding(WindowInsets.statusBars),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (window == null) return@Row

        Row(
            modifier = Modifier
                .weight(1f)
                .horizontalScroll(rememberScrollState()),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            window.tabs.forEach { tab ->
                val isActive = tab.id == window.activeTabId
                Box(
                    modifier = Modifier
                        .padding(horizontal = 2.dp)
                        .height(28.dp)
                        .widthIn(min = 80.dp, max = 160.dp)
                        .background(
                            if (isActive) Color(0xFF2d2d3a) else Color.Transparent,
                            RoundedCornerShape(6.dp),
                        )
                        .clickable { onTabClick(tab.id) }
                        .padding(horizontal = 8.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = tab.title,
                        color = if (isActive) Color.White else Color(0xFF9090a0),
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }

        IconButton(onClick = onNewTab, modifier = Modifier.size(36.dp)) {
            Icon(
                Icons.Default.Add,
                contentDescription = "New tab",
                tint = Color(0xFF9090a0),
                modifier = Modifier.size(16.dp),
            )
        }
    }
}
