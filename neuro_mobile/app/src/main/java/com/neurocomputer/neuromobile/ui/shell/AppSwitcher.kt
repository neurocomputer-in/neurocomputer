package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.APP_LIST
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.data.model.WindowState
import com.neurocomputer.neuromobile.ui.components.AppIcon

private val Backdrop = Color(0xE6000000)
private val CardBg = Color(0xFF1a1a24)
private val CardActive = Color(0xFF2d2d4a)
private val Border = Color(0xFF2a2a3a)
private val Muted = Color(0xFF8a8a9a)

/**
 * Unified switcher: open windows up top, full app grid below to launch new
 * windows in one tap (no separate "+ New Window" → AppPicker hop).
 *
 * Tapping a window card focuses it. Tapping an app icon launches a fresh
 * window for that app and dismisses the switcher.
 */
@Composable
fun AppSwitcher(
    windows: List<WindowState>,
    activeWindowId: String?,
    onFocus: (String) -> Unit,
    onClose: (String) -> Unit,
    onDismiss: () -> Unit,
    onLaunchApp: (AppId) -> Unit,
) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Backdrop)
            // Tap-to-dismiss on the backdrop. Child cards have their own
            // clickable modifiers which consume the gesture, so taps on
            // windows / app icons won't bubble up here.
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onDismiss,
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.statusBars)
                .windowInsetsPadding(WindowInsets.navigationBars)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (windows.isNotEmpty()) {
                SectionHeader("OPEN WINDOWS")
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    windows.forEach { win ->
                        WindowCard(
                            win = win,
                            active = win.id == activeWindowId,
                            onFocus = { onFocus(win.id) },
                            onClose = { onClose(win.id) },
                        )
                    }
                }
            }

            SectionHeader(if (windows.isEmpty()) "LAUNCH APP" else "LAUNCH NEW")
            AppGrid(onPick = onLaunchApp)
        }
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
private fun WindowCard(
    win: WindowState,
    active: Boolean,
    onFocus: () -> Unit,
    onClose: () -> Unit,
) {
    val activeTab = win.tabs.find { it.id == win.activeTabId }
    val app = activeTab?.let { APP_MAP[it.appId] }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (active) CardActive else CardBg, RoundedCornerShape(12.dp))
            .border(1.dp, if (active) Color(0xFF8B5CF6).copy(alpha = 0.6f) else Border, RoundedCornerShape(12.dp))
            .clickable(onClick = onFocus)
            .padding(horizontal = 12.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (app != null) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(
                        if (app.iconResId != null) Color.Transparent
                        else app.color.copy(alpha = 0.85f)
                    ),
                contentAlignment = Alignment.Center,
            ) {
                AppIcon(app = app, size = if (app.iconResId != null) 36.dp else 24.dp)
            }
        }
        Column(Modifier.weight(1f)) {
            Text(
                text = activeTab?.title ?: "Window",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "${win.tabs.size} tab${if (win.tabs.size != 1) "s" else ""}",
                color = Muted,
                fontSize = 12.sp,
            )
        }
        Box(
            modifier = Modifier
                .size(28.dp)
                .clickable(onClick = onClose),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Default.Close, "Close window", tint = Muted, modifier = Modifier.size(16.dp))
        }
    }
}

@Composable
private fun AppGrid(onPick: (AppId) -> Unit) {
    // Bound the grid to a sensible max height so the parent can still scroll
    // when there are many apps. With LazyVerticalGrid inside a vertical
    // Column we need an explicit height, otherwise it crashes — `heightIn`
    // gives the layout an upper bound while still letting the grid handle
    // its own scrolling internally.
    LazyVerticalGrid(
        columns = GridCells.Fixed(4),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(max = 480.dp)
            .background(CardBg, RoundedCornerShape(12.dp))
            .border(1.dp, Border, RoundedCornerShape(12.dp))
            .padding(12.dp),
        contentPadding = PaddingValues(4.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(APP_LIST) { app ->
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .clickable { onPick(app.id) }
                    .padding(vertical = 4.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            if (app.iconResId != null) Color.Transparent
                            else app.color.copy(alpha = 0.9f)
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    AppIcon(app = app, size = if (app.iconResId != null) 44.dp else 28.dp)
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = app.name,
                    color = Color.White,
                    fontSize = 10.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

