package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.History
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
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
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(NeuroColors.BackgroundMid)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Tabs scrollable area (full width since history moved to header)
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically
        ) {
            tabs.forEach { tab ->
                TabItem(
                    tab = tab,
                    onSelect = { onTabSelect(tab.cid) },
                    onClose = { onTabClose(tab.cid) },
                    onRename = { newTitle -> onTabRename(tab.cid, newTitle) }
                )
                Spacer(modifier = Modifier.width(4.dp))
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

    val backgroundColor = if (tab.isActive) NeuroColors.GlassPrimary else NeuroColors.GlassPrimary.copy(alpha = 0.3f)
    val textColor = if (tab.isActive) NeuroColors.TextPrimary else NeuroColors.TextMuted
    val borderColor = if (tab.isActive) NeuroColors.Primary else NeuroColors.BorderAccent.copy(alpha = 0.3f)

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
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .height(36.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(backgroundColor)
                .border(1.dp, borderColor, RoundedCornerShape(6.dp))
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { onSelect() },
                        onLongPress = { showMenu = true }
                    )
                }
                .padding(horizontal = 12.dp)
        ) {
            Text(
                text = tab.title.ifEmpty { "New Chat" },
                color = textColor,
                fontSize = 13.sp,
                fontWeight = if (tab.isActive) FontWeight.Medium else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.widthIn(max = 140.dp)
            )
        }

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
