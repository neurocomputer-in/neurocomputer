package com.neurocomputer.neuromobile.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.domain.model.NoProject
import com.neurocomputer.neuromobile.domain.model.Project
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectSwitcherSheet(
    projects: List<Project>,
    selectedProject: Project,
    onSelectProject: (Project) -> Unit,
    onCreateProject: (String) -> Unit,
    onRenameProject: (String, String) -> Unit,
    onDeleteProject: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var showNewProjectInput by remember { mutableStateOf(false) }
    var newProjectName by remember { mutableStateOf("") }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = NeuroColors.BackgroundMid,
        shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
        dragHandle = {
            Box(
                modifier = Modifier
                    .padding(top = 12.dp, bottom = 4.dp)
                    .width(40.dp)
                    .height(4.dp)
                    .background(NeuroColors.BorderAccent, CircleShape)
            )
        }
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Switch Project",
                    color = NeuroColors.TextPrimary,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, null, tint = NeuroColors.TextMuted, modifier = Modifier.size(20.dp))
                }
            }

            // Project list
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(projects, key = { it.id ?: "__no_project__" }) { project ->
                    ProjectRow(
                        project = project,
                        isSelected = project.id == selectedProject.id,
                        onSelect = { onSelectProject(project); onDismiss() },
                        onRename = { newName -> project.id?.let { onRenameProject(it, newName) } },
                        onDelete = { project.id?.let { onDeleteProject(it) } }
                    )
                }
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = NeuroColors.BorderSubtle, thickness = 0.5.dp)
            Spacer(Modifier.height(12.dp))

            // New project input
            if (showNewProjectInput) {
                OutlinedTextField(
                    value = newProjectName,
                    onValueChange = { newProjectName = it },
                    placeholder = { Text("Project name", color = NeuroColors.TextDim, fontSize = 14.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeuroColors.Primary,
                        unfocusedBorderColor = NeuroColors.BorderAccent,
                        focusedTextColor = NeuroColors.TextPrimary,
                        unfocusedTextColor = NeuroColors.TextPrimary,
                        cursorColor = NeuroColors.Primary
                    ),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = {
                        if (newProjectName.isNotBlank()) {
                            onCreateProject(newProjectName.trim())
                            newProjectName = ""
                            showNewProjectInput = false
                        }
                    }),
                    trailingIcon = {
                        Row {
                            IconButton(onClick = {
                                if (newProjectName.isNotBlank()) {
                                    onCreateProject(newProjectName.trim())
                                    newProjectName = ""
                                    showNewProjectInput = false
                                }
                            }) {
                                Icon(Icons.Default.Check, null, tint = NeuroColors.Primary, modifier = Modifier.size(18.dp))
                            }
                            IconButton(onClick = { showNewProjectInput = false; newProjectName = "" }) {
                                Icon(Icons.Default.Close, null, tint = NeuroColors.TextMuted, modifier = Modifier.size(18.dp))
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                )
            } else {
                // + New Project button
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(NeuroColors.PrimaryGlow, RoundedCornerShape(14.dp))
                        .border(0.5.dp, NeuroColors.PrimaryBorderMid, RoundedCornerShape(14.dp))
                        .clickable { showNewProjectInput = true }
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(Icons.Default.Add, null, tint = NeuroColors.Primary, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("New Project", color = NeuroColors.Primary, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                }
            }
        }
    }
}

@Composable
private fun ProjectRow(
    project: Project,
    isSelected: Boolean,
    onSelect: () -> Unit,
    onRename: (String) -> Unit,
    onDelete: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }
    var showRenameDialog by remember { mutableStateOf(false) }
    var renameText by remember { mutableStateOf(project.name) }
    val haptic = LocalHapticFeedback.current
    val isNoProject = project.id == null

    val bgColor by animateColorAsState(
        if (isSelected) NeuroColors.PrimaryGlow else Color.Transparent,
        tween(200), label = "rowBg"
    )
    val borderColor by animateColorAsState(
        if (isSelected) NeuroColors.PrimaryBorderMid else NeuroColors.BorderSubtle,
        tween(200), label = "rowBorder"
    )

    if (showRenameDialog) {
        AlertDialog(
            onDismissRequest = { showRenameDialog = false },
            title = { Text("Rename Project", color = NeuroColors.TextPrimary) },
            text = {
                OutlinedTextField(
                    value = renameText,
                    onValueChange = { renameText = it },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeuroColors.Primary,
                        unfocusedBorderColor = NeuroColors.BorderAccent,
                        focusedTextColor = NeuroColors.TextPrimary,
                        unfocusedTextColor = NeuroColors.TextPrimary
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    if (renameText.isNotBlank()) onRename(renameText)
                    showRenameDialog = false
                }) { Text("Rename", color = NeuroColors.Primary) }
            },
            dismissButton = {
                TextButton(onClick = { showRenameDialog = false }) {
                    Text("Cancel", color = NeuroColors.TextSecondary)
                }
            },
            containerColor = NeuroColors.BackgroundMid,
            shape = RoundedCornerShape(16.dp)
        )
    }

    Box {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(bgColor, RoundedCornerShape(14.dp))
                .border(0.5.dp, borderColor, RoundedCornerShape(14.dp))
                .pointerInput(project.id) {
                    detectTapGestures(
                        onTap = { onSelect() },
                        onLongPress = {
                            if (!isNoProject) {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                                showMenu = true
                            }
                        }
                    )
                }
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Color dot
            val dotColor = try {
                Color(android.graphics.Color.parseColor(project.color))
            } catch (_: Exception) { NeuroColors.Primary }

            Box(
                modifier = Modifier
                    .size(10.dp)
                    .background(dotColor, CircleShape)
            )
            Spacer(Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = project.name,
                    color = if (isSelected) NeuroColors.TextPrimary else NeuroColors.TextSecondary,
                    fontSize = 14.sp,
                    fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (project.conversationCount > 0) {
                    Text(
                        text = "${project.conversationCount} conversation${if (project.conversationCount != 1) "s" else ""}",
                        color = NeuroColors.TextDim,
                        fontSize = 11.sp
                    )
                }
            }

            if (isSelected) {
                Icon(Icons.Default.Check, null, tint = NeuroColors.Primary, modifier = Modifier.size(16.dp))
            } else if (!isNoProject) {
                Icon(Icons.Default.ChevronRight, null, tint = NeuroColors.TextDim, modifier = Modifier.size(16.dp))
            }
        }

        if (!isNoProject) {
            DropdownMenu(
                expanded = showMenu,
                onDismissRequest = { showMenu = false },
                modifier = Modifier.background(NeuroColors.GlassPrimary, RoundedCornerShape(12.dp))
            ) {
                DropdownMenuItem(
                    text = { Text("Rename", color = NeuroColors.TextPrimary) },
                    onClick = { showMenu = false; renameText = project.name; showRenameDialog = true },
                    leadingIcon = { Icon(Icons.Default.Edit, null, tint = NeuroColors.TextSecondary) }
                )
                DropdownMenuItem(
                    text = { Text("Delete", color = NeuroColors.Error) },
                    onClick = { showMenu = false; onDelete() },
                    leadingIcon = { Icon(Icons.Default.Delete, null, tint = NeuroColors.Error) }
                )
            }
        }
    }
}
