package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.WindowState
import com.neurocomputer.neuromobile.domain.model.Project
import com.neurocomputer.neuromobile.domain.model.Workspace
import com.neurocomputer.neuromobile.ui.components.AppIcon

private val SheetBg = Color(0xFF111118)
private val Surface = Color(0xFF1a1a24)
private val Border = Color(0xFF2a2a3a)
private val Muted = Color(0xFF8a8a9a)
private val Accent = Color(0xFF8B5CF6)

/**
 * Bottom sheet shown when the user taps the hamburger in the tab strip.
 * Contains:
 *   - Current workspace card (tap to change → expanded list of workspaces)
 *   - Projects list (tap to filter)
 *   - "App Switcher" quick-action that opens the window switcher
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MobileControlSheet(
    wsConnected: Boolean = false,
    workspaces: List<Workspace>,
    currentWorkspaceId: String,
    projects: List<Project>,
    currentProjectId: String?,
    windows: List<WindowState>,
    activeWindowId: String?,
    onFocusWindow: (String) -> Unit,
    onSelectWorkspace: (String) -> Unit,
    onSelectProject: (String?) -> Unit,
    onOpenAppSwitcher: () -> Unit,
    onGoHome: () -> Unit,
    onDismiss: () -> Unit,
) {
    var showWorkspacePicker by remember { mutableStateOf(false) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val current = workspaces.firstOrNull { it.id == currentWorkspaceId }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = SheetBg,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            BackendStatusRow(wsConnected)
            SectionHeader("WORKSPACE")
            WorkspaceCard(
                workspace = current,
                onTap = { showWorkspacePicker = !showWorkspacePicker },
                expanded = showWorkspacePicker,
            )

            if (showWorkspacePicker) {
                workspaces.forEach { ws ->
                    WorkspaceRow(
                        ws = ws,
                        selected = ws.id == currentWorkspaceId,
                        onClick = {
                            onSelectWorkspace(ws.id)
                            showWorkspacePicker = false
                        },
                    )
                }
            }

            ProjectsSection(
                projects = projects,
                currentProjectId = currentProjectId,
                onSelectProject = onSelectProject,
            )

            if (windows.isNotEmpty()) {
                OpenWindowsSection(
                    windows = windows,
                    activeWindowId = activeWindowId,
                    onFocusWindow = onFocusWindow,
                )
            }

            HomeButton(onGoHome)
            AppSwitcherButton(onOpenAppSwitcher)

            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun BackendStatusRow(connected: Boolean) {
    val dotColor = if (connected) Color(0xFF22c55e) else Color(0xFF6b7280)
    val label = if (connected) "Backend connected" else "Backend disconnected"

    val pulse = rememberInfiniteTransition(label = "pulse")
    val scale by pulse.animateFloat(
        initialValue = 1f, targetValue = if (connected) 1.5f else 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "scale",
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                if (connected) Color(0xFF052e16) else Color(0xFF1a1a24),
                RoundedCornerShape(10.dp),
            )
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            // Pulsing ring (only when connected)
            if (connected) {
                Box(
                    modifier = Modifier
                        .size(14.dp)
                        .scale(scale)
                        .background(dotColor.copy(alpha = 0.25f), CircleShape),
                )
            }
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(dotColor, CircleShape),
            )
        }
        Text(
            text = label,
            color = if (connected) Color(0xFF86efac) else Muted,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(
        text = text,
        color = Muted,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.sp,
    )
}

@Composable
private fun WorkspaceCard(
    workspace: Workspace?,
    onTap: () -> Unit,
    expanded: Boolean,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Surface, RoundedCornerShape(12.dp))
            .border(1.dp, Border, RoundedCornerShape(12.dp))
            .clickable(onClick = onTap)
            .padding(horizontal = 12.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        WorkspaceBadge(workspace)
        Column(Modifier.weight(1f)) {
            Text(
                text = workspace?.name ?: "Loading…",
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = if (expanded) "Tap to collapse" else "Tap to switch",
                color = Muted,
                fontSize = 12.sp,
            )
        }
        Icon(
            Icons.Default.ChevronRight,
            contentDescription = null,
            tint = Muted,
            modifier = Modifier.size(20.dp),
        )
    }
}

@Composable
private fun WorkspaceBadge(workspace: Workspace?) {
    val color = parseHexColor(workspace?.color) ?: Accent
    Box(
        modifier = Modifier
            .size(36.dp)
            .background(color, CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        // Fall back to first initial when emoji absent. Most workspaces have one.
        val label = workspace?.name?.firstOrNull()?.uppercase() ?: "?"
        Text(
            text = workspace?.emoji?.takeIf { it.isNotBlank() } ?: label,
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun WorkspaceRow(ws: Workspace, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 4.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            modifier = Modifier
                .size(20.dp)
                .background(parseHexColor(ws.color) ?: Accent, CircleShape),
        )
        Text(
            text = ws.name,
            color = if (selected) Color.White else Muted,
            fontSize = 14.sp,
            modifier = Modifier.weight(1f),
        )
        if (selected) {
            Icon(Icons.Default.Check, null, tint = Accent, modifier = Modifier.size(16.dp))
        }
    }
}

@Composable
private fun ProjectsSection(
    projects: List<Project>,
    currentProjectId: String?,
    onSelectProject: (String?) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        SectionHeader("PROJECTS")
        // "All Projects" pseudo-row — passes null to clear the filter.
        ProjectRow(
            label = "All Projects",
            color = Muted,
            selected = currentProjectId == null,
            icon = { Icon(Icons.Default.FolderOpen, null, tint = Muted, modifier = Modifier.size(16.dp)) },
            onClick = { onSelectProject(null) },
        )
        projects.forEach { p ->
            ProjectRow(
                label = p.name,
                color = parseHexColor(p.color) ?: Accent,
                selected = currentProjectId == p.id,
                onClick = { onSelectProject(p.id) },
            )
        }
    }
}

@Composable
private fun ProjectRow(
    label: String,
    color: Color,
    selected: Boolean,
    icon: (@Composable () -> Unit)? = null,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                if (selected) Surface else Color.Transparent,
                RoundedCornerShape(8.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (icon != null) icon()
        else Box(Modifier.size(10.dp).background(color, CircleShape))
        Text(
            text = label,
            color = if (selected) Color.White else Color(0xFFcfcfd6),
            fontSize = 14.sp,
            modifier = Modifier.weight(1f),
        )
        if (selected) {
            Icon(Icons.Default.Check, null, tint = Accent, modifier = Modifier.size(16.dp))
        }
    }
}

@Composable
private fun OpenWindowsSection(
    windows: List<WindowState>,
    activeWindowId: String?,
    onFocusWindow: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        SectionHeader("OPEN WINDOWS")
        // Horizontal scroll — handles many windows without forcing the sheet
        // to grow vertically. Each chip is fixed-width so cards line up neatly
        // and the user can swipe through.
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            windows.forEach { win ->
                WindowChip(
                    win = win,
                    active = win.id == activeWindowId,
                    onClick = { onFocusWindow(win.id) },
                )
            }
        }
    }
}

@Composable
private fun WindowChip(
    win: WindowState,
    active: Boolean,
    onClick: () -> Unit,
) {
    val activeTab = win.tabs.find { it.id == win.activeTabId }
    val app = activeTab?.let { APP_MAP[it.appId] }
    Row(
        modifier = Modifier
            .width(180.dp)
            .background(Surface, RoundedCornerShape(10.dp))
            .border(
                width = 1.dp,
                color = if (active) Accent.copy(alpha = 0.6f) else Border,
                shape = RoundedCornerShape(10.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (app != null) {
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(
                        if (app.iconResId != null) Color.Transparent
                        else app.color.copy(alpha = 0.85f)
                    ),
                contentAlignment = Alignment.Center,
            ) {
                AppIcon(app = app, size = if (app.iconResId != null) 28.dp else 18.dp)
            }
        }
        Column(Modifier.weight(1f)) {
            Text(
                text = activeTab?.title ?: "Window",
                color = Color.White,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "${win.tabs.size} tab${if (win.tabs.size != 1) "s" else ""}",
                color = Muted,
                fontSize = 11.sp,
            )
        }
    }
}

@Composable
private fun HomeButton(onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Surface, RoundedCornerShape(12.dp))
            .border(1.dp, Border, RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(Icons.Default.Home, null, tint = Accent, modifier = Modifier.size(22.dp))
        Text("Home", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun AppSwitcherButton(onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Surface, RoundedCornerShape(12.dp))
            .border(1.dp, Border, RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(Icons.Default.Apps, null, tint = Accent, modifier = Modifier.size(22.dp))
        Text("App Switcher", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
    }
}

private fun parseHexColor(hex: String?): Color? {
    val s = hex?.removePrefix("#") ?: return null
    return try {
        val v = s.toLong(16)
        when (s.length) {
            6 -> Color(0xFF000000 or v)
            8 -> Color(v)
            else -> null
        }
    } catch (_: Exception) { null }
}
