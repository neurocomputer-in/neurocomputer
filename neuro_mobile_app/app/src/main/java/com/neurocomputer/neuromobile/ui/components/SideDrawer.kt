package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

data class DrawerMenuItem(
    val id: String,
    val title: String,
    val icon: ImageVector,
    val badge: String? = null,
    val badgeColor: Color = NeuroColors.Primary
)

data class DrawerSection(
    val title: String,
    val items: List<DrawerMenuItem>
)

private val MENU_SECTIONS = listOf(
    DrawerSection("Remote PC", listOf(
        DrawerMenuItem("remote_pc", "Remote PC", Icons.Default.DesktopWindows)
    )),
    DrawerSection("Tools", listOf(
        DrawerMenuItem("voice_settings", "Voice Settings", Icons.Default.Mic),
        DrawerMenuItem("ocr", "Screen OCR", Icons.Default.TextFields),
        DrawerMenuItem("shortcuts", "Shortcuts", Icons.Default.Bolt),
        DrawerMenuItem("overlay", "Floating Actions", Icons.Default.WebAsset)
    )),
    DrawerSection("App", listOf(
        DrawerMenuItem("settings", "Settings", Icons.Default.Settings),
        DrawerMenuItem("about", "About", Icons.Default.Info)
    ))
)

@Composable
fun SideDrawerPanel(
    onClose: () -> Unit,
    onSettingsClick: () -> Unit,
    onScreenShareClick: () -> Unit,
    onVoiceSettingsClick: () -> Unit,
    onOcrClick: () -> Unit,
    onShortcutsClick: () -> Unit,
    onAboutClick: () -> Unit,
    onOverlayToggle: () -> Unit,
    remotePcConnected: Boolean = false,
    isOverlayEnabled: Boolean = false
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
                    .width(300.dp)
                    .fillMaxHeight()
                    .background(NeuroColors.BackgroundDark)
                    .clickable(enabled = false) { }
            ) {
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .blur(15.dp)
                        .background(NeuroColors.BackgroundDark.copy(alpha = 0.5f))
                )
                Column(
                    modifier = Modifier
                        .matchParentSize()
                        .padding(top = 48.dp)
                ) {
                    LazyColumn(
                        modifier = Modifier.weight(1f)
                    ) {
                        item {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 20.dp, vertical = 16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(52.dp)
                                        .clip(CircleShape)
                                        .background(NeuroColors.GlassPrimary),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Image(
                                        painter = painterResource(id = com.neurocomputer.neuromobile.R.drawable.logo),
                                        contentDescription = "Neuro",
                                        modifier = Modifier.size(36.dp),
                                        contentScale = ContentScale.Fit
                                    )
                                }
                                Spacer(modifier = Modifier.width(14.dp))
                                Column {
                                    Text(
                                        text = "Neuro",
                                        color = NeuroColors.TextPrimary,
                                        fontSize = 18.sp
                                    )
                                    Text(
                                        text = "AI Assistant",
                                        color = NeuroColors.TextMuted,
                                        fontSize = 13.sp
                                    )
                                }
                            }
                        }

                        items(MENU_SECTIONS) { section ->
                            Text(
                                text = section.title.uppercase(),
                                color = NeuroColors.TextDim,
                                fontSize = 11.sp,
                                letterSpacing = 1.sp,
                                modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp)
                            )
                            section.items.forEach { item ->
                                val isConnected = when (item.id) {
                                    "remote_pc" -> remotePcConnected
                                    "overlay" -> isOverlayEnabled
                                    else -> false
                                }
                                DrawerItem(
                                    item = item,
                                    isConnected = isConnected,
                                    onClick = {
                                        when (item.id) {
                                            "settings" -> onSettingsClick()
                                            "remote_pc" -> onScreenShareClick()
                                            "voice_settings" -> onVoiceSettingsClick()
                                            "ocr" -> onOcrClick()
                                            "shortcuts" -> onShortcutsClick()
                                            "overlay" -> onOverlayToggle()
                                            "about" -> onAboutClick()
                                        }
                                        onClose()
                                    }
                                )
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                    }

                    HorizontalDivider(color = NeuroColors.BorderSubtle)

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "Neuro",
                            color = NeuroColors.TextMuted,
                            fontSize = 14.sp
                        )
                        Text(
                            text = "Version 1.0.0",
                            color = NeuroColors.TextDim,
                            fontSize = 12.sp
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun DrawerItem(
    item: DrawerMenuItem,
    isConnected: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable { onClick() }
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(
                    if (isConnected) NeuroColors.Success.copy(alpha = 0.15f)
                    else NeuroColors.GlassPrimary,
                    RoundedCornerShape(19.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                item.icon,
                contentDescription = null,
                tint = if (isConnected) NeuroColors.Success else NeuroColors.TextPrimary,
                modifier = Modifier.size(20.dp)
            )
        }
        Spacer(modifier = Modifier.width(14.dp))
        Text(
            text = item.title,
            color = NeuroColors.TextPrimary,
            fontSize = 15.sp,
            modifier = Modifier.weight(1f)
        )
        if (isConnected) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(NeuroColors.Success, CircleShape)
            )
        }
        Spacer(modifier = Modifier.width(8.dp))
        Icon(
            Icons.AutoMirrored.Filled.KeyboardArrowRight,
            contentDescription = null,
            tint = NeuroColors.TextDim,
            modifier = Modifier.size(18.dp)
        )
    }
}
