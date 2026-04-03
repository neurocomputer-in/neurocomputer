package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.domain.model.ConversationSummary
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

@Composable
fun ChatHistoryDrawer(
    onClose: () -> Unit,
    onChatSelect: (String) -> Unit,
    onChatRename: (String, String) -> Unit,
    onChatDelete: (String) -> Unit,
    conversations: List<ConversationSummary> = emptyList()
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NeuroColors.OverlayDark.copy(alpha = 0.6f))
            .clickable { onClose() }
    ) {
        Row(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .width(320.dp)
                    .fillMaxHeight()
                    .background(NeuroColors.BackgroundDark)
                    .clickable(enabled = false) { }
            ) {
                Column(
                    modifier = Modifier
                        .matchParentSize()
                        .padding(top = 48.dp)
                ) {
                    // Header
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 20.dp, vertical = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Chat History",
                            color = NeuroColors.TextPrimary,
                            fontSize = 18.sp
                        )
                        Spacer(modifier = Modifier.weight(1f))
                        IconButton(onClick = onClose) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Close",
                                tint = NeuroColors.TextPrimary
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Chat List
                    LazyColumn(
                        modifier = Modifier.weight(1f)
                    ) {
                        if (conversations.isEmpty()) {
                            item {
                                Row(
                                    modifier = Modifier
                                        .padding(horizontal = 20.dp, vertical = 24.dp)
                                ) {
                                    Text(
                                        text = "No chats yet",
                                        color = NeuroColors.TextMuted,
                                        fontSize = 14.sp
                                    )
                                }
                            }
                        } else {
                            val limitedConversations = conversations.take(20)
                            items(limitedConversations) { conv ->
                                HistoryItem(
                                    conv = conv,
                                    onSelect = {
                                        onChatSelect(conv.id)
                                        onClose()
                                    },
                                    onRename = { newTitle -> onChatRename(conv.id, newTitle) },
                                    onDelete = { onChatDelete(conv.id) }
                                )
                            }
                        }
                    }
                }
            }
            Spacer(modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun HistoryItem(
    conv: ConversationSummary,
    onSelect: () -> Unit,
    onRename: (String) -> Unit,
    onDelete: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }
    var showRenameDialog by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var renameText by remember { mutableStateOf(conv.title) }

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

    // Delete confirmation dialog
    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete Chat?", color = Color.White) },
            text = { Text("This will permanently delete this chat.", color = Color.White) },
            confirmButton = {
                TextButton(onClick = {
                    onDelete()
                    showDeleteDialog = false
                }) {
                    Text("Delete", color = NeuroColors.Error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteDialog = false }) {
                    Text("Cancel", color = Color.White)
                }
            },
            containerColor = NeuroColors.BackgroundMid
        )
    }

    Box {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { onSelect() },
                        onLongPress = { showMenu = true }
                    )
                }
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .background(NeuroColors.GlassPrimary, RoundedCornerShape(18.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Chat,
                    contentDescription = null,
                    tint = NeuroColors.TextPrimary,
                    modifier = Modifier.size(18.dp)
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = conv.title.ifEmpty { "New Chat" },
                    color = NeuroColors.TextPrimary,
                    fontSize = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (conv.lastMessage.isNotEmpty()) {
                    Text(
                        text = conv.lastMessage,
                        color = NeuroColors.TextMuted,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
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
                    renameText = conv.title
                    showRenameDialog = true
                },
                leadingIcon = {
                    Icon(Icons.Default.Edit, contentDescription = null, tint = Color.White)
                }
            )
            DropdownMenuItem(
                text = { Text("Delete", color = NeuroColors.Error) },
                onClick = {
                    showMenu = false
                    showDeleteDialog = true
                },
                leadingIcon = {
                    Icon(Icons.Default.Delete, contentDescription = null, tint = NeuroColors.Error)
                }
            )
        }
    }
}
