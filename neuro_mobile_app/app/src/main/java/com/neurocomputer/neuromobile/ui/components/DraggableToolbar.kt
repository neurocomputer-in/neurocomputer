package com.neurocomputer.neuromobile.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import com.neurocomputer.neuromobile.domain.model.AgentType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import com.neurocomputer.neuromobile.R
import androidx.compose.foundation.Image
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import kotlin.math.roundToInt

@Composable
fun DraggableToolbarOverlay(
    offset: Offset,
    onOffsetChange: (Offset) -> Unit,
    isVoiceTyping: Boolean,
    isKeyboardOpen: Boolean,
    isScrollMode: Boolean,
    isClickMode: Boolean,
    isFocusMode: Boolean,
    selectedAgentName: String,
    selectedAgentType: AgentType = AgentType.NEURO,
    onVoiceTypeToggle: () -> Unit,
    onSubmitVoice: () -> Unit,
    onCancelVoice: () -> Unit,
    onSendKey: (String) -> Unit,
    onToggleKeyboard: () -> Unit,
    onToggleScrollMode: () -> Unit,
    onToggleClickMode: () -> Unit,
    onToggleFocusMode: () -> Unit,
    onAgentClick: () -> Unit,
    showAgentButton: Boolean = true,
    isRotationLocked: Boolean = false,
    onRotationLockToggle: (() -> Unit)? = null,
) {
    var isExpanded by remember { mutableStateOf(false) }
    var showLabels by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .offset { IntOffset(offset.x.roundToInt(), offset.y.roundToInt()) }
            .zIndex(9999f)
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    onOffsetChange(
                        Offset(
                            x = (offset.x + dragAmount.x).coerceIn(0f, 2000f),
                            y = (offset.y + dragAmount.y).coerceIn(0f, 2000f)
                        )
                    )
                }
            }
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            if (showAgentButton) {
                // Agent selector button - always visible at top
                AgentToolbarButton(
                    agentName = selectedAgentName,
                    agentType = selectedAgentType,
                    onClick = onAgentClick
                )

                Spacer(modifier = Modifier.height(4.dp))
            }

            // Drag handle
            Box(
                modifier = Modifier
                    .width(40.dp)
                    .height(4.dp)
                    .background(NeuroColors.BorderLight.copy(alpha = 0.5f), RoundedCornerShape(2.dp))
            )

            Spacer(modifier = Modifier.height(4.dp))

            // Main toolbar - using Column for vertical look
            Column(
                modifier = Modifier
                    .clip(RoundedCornerShape(32.dp))
                    .background(NeuroColors.BackgroundMid.copy(alpha = 0.45f))
                    .border(1.dp, NeuroColors.BorderSubtle.copy(alpha = 0.3f), RoundedCornerShape(32.dp))
                    .padding(horizontal = 4.dp, vertical = 6.dp)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {

                // Label toggle
                ToolbarButton(
                    icon = if (showLabels) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                    label = if (showLabels) "Labels" else "",
                    isActive = showLabels,
                    activeColor = Color(0xFF8B5CF6.toInt()),
                    onClick = { showLabels = !showLabels }
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Voice type toggle
                ToolbarButton(
                    icon = if (isVoiceTyping) Icons.Default.MicOff else Icons.Default.Mic,
                    label = if (showLabels) "Mic" else "",
                    isActive = isVoiceTyping,
                    activeColor = Color(0xFFFF5555.toInt()),
                    onClick = onVoiceTypeToggle
                )

                Spacer(modifier = Modifier.height(4.dp))

                Box(
                    modifier = Modifier
                        .height(1.dp)
                        .width(20.dp)
                        .background(NeuroColors.BorderSubtle.copy(alpha = 0.5f))
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Enter/Submit
                ToolbarButton(
                    icon = Icons.Default.KeyboardReturn,
                    label = if (showLabels) "Enter" else "",
                    isActive = isVoiceTyping,
                    activeColor = Color(0xFF50FA7B.toInt()),
                    onClick = {
                        if (isVoiceTyping) onSubmitVoice()
                        else onSendKey("Return")
                    }
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Backspace/Cancel
                ToolbarButton(
                    icon = if (isVoiceTyping) Icons.Default.Cancel else Icons.Default.Backspace,
                    label = if (showLabels) "Back" else "",
                    isActive = isVoiceTyping,
                    activeColor = Color(0xFFFF5555.toInt()),
                    onClick = {
                        if (isVoiceTyping) onCancelVoice()
                        else onSendKey("BackSpace")
                    }
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Space
                ToolbarButton(
                    icon = Icons.Default.SpaceBar,
                    label = if (showLabels) "Space" else "",
                    isActive = false,
                    activeColor = Color.Unspecified,
                    onClick = { onSendKey("space") }
                )

                Spacer(modifier = Modifier.height(4.dp))

                Box(
                    modifier = Modifier
                        .height(1.dp)
                        .width(20.dp)
                        .background(NeuroColors.BorderSubtle.copy(alpha = 0.5f))
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Keyboard toggle
                ToolbarButton(
                    icon = if (isKeyboardOpen) Icons.Default.KeyboardHide else Icons.Default.Keyboard,
                    label = if (showLabels) "Keys" else "",
                    isActive = isKeyboardOpen,
                    activeColor = Color(0xFF8B5CF6.toInt()),
                    onClick = onToggleKeyboard
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Scroll mode
                ToolbarButton(
                    icon = Icons.Default.Swipe,
                    label = if (showLabels) "Scroll" else "",
                    isActive = isScrollMode,
                    activeColor = Color(0xFF8BE9FD.toInt()),
                    onClick = onToggleScrollMode
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Click mode
                ToolbarButton(
                    icon = Icons.Default.TouchApp,
                    label = if (showLabels) "Click" else "",
                    isActive = isClickMode,
                    activeColor = Color(0xFF50FA7B.toInt()),
                    onClick = onToggleClickMode
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Focus mode
                ToolbarButton(
                    icon = Icons.Default.CenterFocusStrong,
                    label = if (showLabels) "Focus" else "",
                    isActive = isFocusMode,
                    activeColor = Color(0xFFF1FA8C.toInt()),
                    onClick = onToggleFocusMode
                )

                // Rotation lock (only shown when wired by the caller)
                if (onRotationLockToggle != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    ToolbarButton(
                        icon = if (isRotationLocked) Icons.Default.Lock else Icons.Default.LockOpen,
                        label = if (showLabels) (if (isRotationLocked) "Locked" else "Auto") else "",
                        isActive = isRotationLocked,
                        activeColor = Color(0xFFE57373.toInt()),
                        onClick = onRotationLockToggle,
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Expand/Collapse
                ToolbarButton(
                    icon = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    label = "",
                    isActive = false,
                    activeColor = Color.Unspecified,
                    onClick = { isExpanded = !isExpanded }
                )
            }

            // Expanded shortcuts
            if (isExpanded) {
                Spacer(modifier = Modifier.height(6.dp))

                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(NeuroColors.BackgroundMid.copy(alpha = 0.35f))
                        .border(1.dp, NeuroColors.BorderSubtle, RoundedCornerShape(16.dp))
                        .padding(6.dp)
                ) {

                    // Row 1: ESC, Tab, Copy, Paste
                    Row {
                        ToolbarButton(icon = Icons.Default.Settings, label = "ESC", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("Escape") })
                        ToolbarButton(icon = Icons.Default.Keyboard, label = "Tab", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("Tab") })
                        ToolbarButton(icon = Icons.AutoMirrored.Filled.Undo, label = "Undo", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("ctrl+z") })
                        ToolbarButton(icon = Icons.AutoMirrored.Filled.Redo, label = "Redo", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("ctrl+y") })
                    }

                    Spacer(modifier = Modifier.height(2.dp))

                    // Row 2: Screenshot, PageUp, PageDown
                    Row {
                        ToolbarButton(icon = Icons.Default.Screenshot, label = "Capture", isActive = false, activeColor = Color.Unspecified, onClick = { /* Screenshot */ })
                        ToolbarButton(icon = Icons.Default.ArrowUpward, label = "PgUp", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("Page_Up") })
                        ToolbarButton(icon = Icons.Default.ArrowDownward, label = "PgDn", isActive = false, activeColor = Color.Unspecified, onClick = { onSendKey("Page_Down") })
                    }
                }
            }
        }
    }
}

@Composable
fun ToolbarButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    isActive: Boolean,
    activeColor: Color,
    onClick: () -> Unit
) {
    val backgroundColor by animateColorAsState(
        targetValue = if (isActive) activeColor.copy(alpha = 0.2f) else Color.Transparent,
        label = "bg"
    )

    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(backgroundColor)
            .clickable { onClick() }
            .padding(2.dp),    // Compact padding
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = if (isActive) activeColor else NeuroColors.TextSecondary,
            modifier = Modifier.size(18.dp)
        )
        if (label.isNotEmpty()) {
            Text(
                text = label,
                color = NeuroColors.TextDim,
                fontSize = 7.sp
            )
        }
    }
}

/**
 * Prominent agent selector button for the floating toolbar.
 * Shows the agent icon with name always visible.
 */
@Composable
fun AgentToolbarButton(
    agentName: String,
    agentType: AgentType,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(NeuroColors.GlassPrimary.copy(alpha = 0.6f))
            .clickable { onClick() }
            .padding(horizontal = 6.dp, vertical = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier.size(20.dp),
            contentAlignment = Alignment.Center
        ) {
            when (agentType) {
                AgentType.NEURO -> Image(
                    painter = painterResource(id = R.drawable.logo),
                    contentDescription = agentName,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
                AgentType.OPENCLAW -> Image(
                    painter = painterResource(id = R.drawable.openclaw_logo),
                    contentDescription = agentName,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
                AgentType.OPENCODE -> Image(
                    painter = painterResource(id = R.drawable.opencode_logo),
                    contentDescription = agentName,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
                AgentType.NEUROUPWORK -> Image(
                    painter = painterResource(id = R.drawable.upwork_logo),
                    contentDescription = agentName,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            }
        }
        Text(
            text = agentName,
            color = NeuroColors.TextPrimary,
            fontSize = 8.sp,
            maxLines = 1
        )
    }
}
