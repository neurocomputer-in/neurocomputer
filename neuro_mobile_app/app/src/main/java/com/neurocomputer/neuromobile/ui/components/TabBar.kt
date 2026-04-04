package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

data class Tab(
    val cid: String,
    val title: String,
    val isActive: Boolean = false
)

@Composable
fun TabBar(
    tabs: List<Tab>,
    onTabSelect: (String) -> Unit,
    onTabClose: (String) -> Unit,
    onTabRename: (String, String) -> Unit,
    onNewTab: () -> Unit = {},
    onHistoryClick: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(38.dp)
            .background(NeuroColors.BackgroundDark)
            .padding(start = 4.dp, end = 4.dp),
        verticalAlignment = Alignment.Bottom
    ) {
        // Scrollable tabs area
        Row(
            modifier = Modifier
                .weight(1f)
                .horizontalScroll(scrollState),
            verticalAlignment = Alignment.Bottom
        ) {
            tabs.forEach { tab ->
                key(tab.cid) {
                    TabItem(
                        tab = tab,
                        onSelect = { onTabSelect(tab.cid) },
                        onClose = { onTabClose(tab.cid) },
                        onRename = { newTitle -> onTabRename(tab.cid, newTitle) }
                    )
                }
            }
        }

        // Tab count + New tab button
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .padding(bottom = 2.dp, start = 4.dp)
        ) {
            if (tabs.isNotEmpty()) {
                Text(
                    text = "${tabs.size}",
                    color = NeuroColors.TextDim,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.padding(end = 2.dp)
                )
            }
            IconButton(
                onClick = onNewTab,
                modifier = Modifier.size(28.dp)
            ) {
                Icon(
                    Icons.Default.Add,
                    contentDescription = "New tab",
                    tint = NeuroColors.TextMuted,
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}

@Composable
private fun TabItem(
    tab: Tab,
    onSelect: () -> Unit,
    onClose: () -> Unit,
    onRename: (String) -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }
    var showRenameDialog by remember { mutableStateOf(false) }
    var renameText by remember { mutableStateOf(tab.title) }

    // Use rememberUpdatedState so pointerInput always calls the latest lambdas
    val currentOnSelect by rememberUpdatedState(onSelect)
    val currentOnClose by rememberUpdatedState(onClose)

    val isActive = tab.isActive

    // VS Code style: active tab has a lighter background and top accent, inactive is dim
    val backgroundColor = if (isActive) NeuroColors.BackgroundMid else Color.Transparent
    val textColor = if (isActive) NeuroColors.TextPrimary else NeuroColors.TextDim
    val topBorder = if (isActive) NeuroColors.Primary else Color.Transparent
    val bottomBorder = if (isActive) NeuroColors.BackgroundMid else NeuroColors.BorderSubtle

    // Rename dialog
    if (showRenameDialog) {
        AlertDialog(
            onDismissRequest = { showRenameDialog = false },
            title = { Text("Rename Chat", color = Color.White) },
            text = {
                OutlinedTextField(
                    value = renameText,
                    onValueChange = { renameText = it },
                    label = { Text("Title") },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeuroColors.Primary,
                        unfocusedBorderColor = NeuroColors.BorderAccent,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    if (renameText.isNotBlank()) {
                        onRename(renameText)
                    }
                    showRenameDialog = false
                }) {
                    Text("Rename", color = NeuroColors.Primary)
                }
            },
            dismissButton = {
                TextButton(onClick = { showRenameDialog = false }) {
                    Text("Cancel", color = Color.White)
                }
            },
            containerColor = NeuroColors.BackgroundMid
        )
    }

    Box {
        Column(
            modifier = Modifier
                .pointerInput(tab.cid) {
                    detectTapGestures(
                        onTap = { currentOnSelect() },
                        onLongPress = { showMenu = true }
                    )
                }
        ) {
            // Top accent line (active indicator)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(2.dp)
                    .background(topBorder)
            )

            // Tab content
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .height(34.dp)
                    .background(backgroundColor)
                    .padding(horizontal = 12.dp)
            ) {
                Text(
                    text = tab.title.ifEmpty { "New Chat" },
                    color = textColor,
                    fontSize = 12.sp,
                    fontWeight = if (isActive) FontWeight.Normal else FontWeight.Light,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.widthIn(max = 120.dp)
                )
            }

            // Bottom line (blends with content area for active tab)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(bottomBorder)
            )
        }

        // Right separator between tabs
        Box(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .width(1.dp)
                .height(20.dp)
                .background(if (!isActive) NeuroColors.BorderSubtle else Color.Transparent)
        )

        DropdownMenu(
            expanded = showMenu,
            onDismissRequest = { showMenu = false },
            modifier = Modifier.background(NeuroColors.BackgroundMid)
        ) {
            DropdownMenuItem(
                text = { Text("Rename", color = Color.White) },
                onClick = {
                    showMenu = false
                    renameText = tab.title
                    showRenameDialog = true
                },
                leadingIcon = {
                    Icon(Icons.Default.Edit, contentDescription = null, tint = Color.White)
                }
            )
            DropdownMenuItem(
                text = { Text("Close", color = NeuroColors.Error) },
                onClick = {
                    showMenu = false
                    onClose()
                },
                leadingIcon = {
                    Icon(Icons.Default.Close, contentDescription = null, tint = NeuroColors.Error)
                }
            )
        }
    }
}
