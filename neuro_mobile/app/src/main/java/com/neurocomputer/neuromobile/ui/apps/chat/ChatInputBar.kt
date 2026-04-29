package com.neurocomputer.neuromobile.ui.apps.chat

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Surface = Color(0xFF1c1c26)
private val InputBg = Color(0xFF161620)
private val Accent = Color(0xFF8B5CF6)
private val MutedText = Color(0xFF8888aa)
private val SubtleBorder = Color(0xFF2a2a3a)

@Composable
fun ChatInputBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    isRecording: Boolean = false,
    recordingSeconds: Int = 0,
    onStartRecording: () -> Unit = {},
    onCancelRecording: () -> Unit = {},
    onSendVoice: () -> Unit = {},
    onStartVoiceCall: () -> Unit = {},
    showModelPicker: Boolean = true,
    showVoiceCall: Boolean = true,
    modelLabel: String = "Auto",
    onOpenModelPicker: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(Color(0xFF111118))
            .windowInsetsPadding(WindowInsets.ime)
            .windowInsetsPadding(WindowInsets.navigationBars)
            .padding(horizontal = 12.dp, vertical = 10.dp),
    ) {
        if (isRecording) {
            VoiceRecordingPanel(
                seconds = recordingSeconds,
                onCancel = onCancelRecording,
                onSend = onSendVoice,
            )
        } else {
            // ---- Composer card: text input on top, controls below ----
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Surface, RoundedCornerShape(22.dp))
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Text field
                Box(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    if (value.isEmpty()) {
                        Text(
                            text = "Ask anything",
                            color = Color(0xFF666677),
                            fontSize = 15.sp,
                        )
                    }
                    BasicTextField(
                        value = value,
                        onValueChange = onValueChange,
                        textStyle = TextStyle(color = Color.White, fontSize = 15.sp),
                        cursorBrush = SolidColor(Accent),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { onSend() }),
                        maxLines = 6,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                // Action row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    // Attach (placeholder — wire up later)
                    SmallIconButton(
                        icon = Icons.Default.AttachFile,
                        contentDescription = "Attach",
                        tint = MutedText,
                        onClick = { /* TODO: attach */ },
                    )

                    if (showModelPicker) {
                        ModelPill(label = modelLabel, onClick = onOpenModelPicker)
                    }

                    Spacer(Modifier.weight(1f))

                    // Voice message mic — always available
                    SmallIconButton(
                        icon = Icons.Default.Mic,
                        contentDescription = "Record voice message",
                        tint = MutedText,
                        onClick = onStartRecording,
                    )

                    // Right-most action: Send if text, else Speak (voice call) for native
                    when {
                        value.isNotBlank() -> SendPill(onClick = onSend)
                        showVoiceCall -> SpeakPill(onClick = onStartVoiceCall)
                        else -> SendPill(onClick = onSend, enabled = false)
                    }
                }
            }
        }
    }
}

@Composable
private fun SmallIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    tint: Color,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .size(36.dp)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription, tint = tint, modifier = Modifier.size(20.dp))
    }
}

@Composable
private fun ModelPill(label: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .background(InputBg, RoundedCornerShape(18.dp))
            .border(1.dp, SubtleBorder, RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(
            Icons.Default.Bolt,
            contentDescription = null,
            tint = Accent,
            modifier = Modifier.size(14.dp),
        )
        Text(
            text = label,
            color = Color.White,
            fontSize = 12.sp,
            maxLines = 1,
            softWrap = false,
            overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
            modifier = Modifier.widthIn(max = 90.dp),
        )
        Icon(
            Icons.Default.KeyboardArrowDown,
            contentDescription = null,
            tint = MutedText,
            modifier = Modifier.size(14.dp),
        )
    }
}

@Composable
private fun SendPill(onClick: () -> Unit, enabled: Boolean = true) {
    val bg = if (enabled) Color.White else Color(0xFF2a2a3a)
    val tint = if (enabled) Color(0xFF111118) else Color(0xFF555566)
    Row(
        modifier = Modifier
            .background(bg, RoundedCornerShape(18.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(
            Icons.AutoMirrored.Filled.Send,
            contentDescription = "Send",
            tint = tint,
            modifier = Modifier.size(16.dp),
        )
        Text(
            text = "Send",
            color = tint,
            fontSize = 13.sp,
            maxLines = 1,
            softWrap = false,
        )
    }
}

@Composable
private fun SpeakPill(onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .background(Color.White, RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        WaveformGlyph()
        Text(
            text = "Speak",
            color = Color(0xFF111118),
            fontSize = 13.sp,
            maxLines = 1,
            softWrap = false,
        )
    }
}

/** Static 3-bar audio glyph used in the Speak pill (idle state). */
@Composable
private fun WaveformGlyph() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        listOf(5.dp, 10.dp, 5.dp).forEach { h ->
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .height(h)
                    .background(Color(0xFF111118), RoundedCornerShape(1.dp)),
            )
        }
    }
}

@Composable
private fun VoiceRecordingPanel(
    seconds: Int,
    onCancel: () -> Unit,
    onSend: () -> Unit,
) {
    // Pulsing red dot + animated waveform-style bars + duration + cancel/send
    val transition = rememberInfiniteTransition(label = "rec")
    val pulse by transition.animateFloat(
        initialValue = 0.4f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(700, easing = EaseInOut), RepeatMode.Reverse),
        label = "pulse",
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Surface, RoundedCornerShape(22.dp))
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        // Cancel
        Box(
            modifier = Modifier
                .size(36.dp)
                .background(Color(0xFF2a2a3a), CircleShape)
                .clickable(onClick = onCancel),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Default.Close, "Cancel", tint = Color.White, modifier = Modifier.size(18.dp))
        }

        // Pulsing red dot
        Box(
            modifier = Modifier
                .size(10.dp)
                .alpha(pulse)
                .background(Color(0xFFef4444), CircleShape),
        )

        // Animated bars + time
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            BarVisualizer(modifier = Modifier.weight(1f))
            Text(
                text = "%01d:%02d".format(seconds / 60, seconds % 60),
                color = Color.White,
                fontSize = 14.sp,
            )
        }

        // Send
        Box(
            modifier = Modifier
                .size(40.dp)
                .background(Color.White, CircleShape)
                .clickable(onClick = onSend),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Default.Check,
                "Send voice",
                tint = Color(0xFF111118),
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun BarVisualizer(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "bars")
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        repeat(18) { i ->
            val h by transition.animateFloat(
                initialValue = 4f,
                targetValue = (10..22).random().toFloat(),
                animationSpec = infiniteRepeatable(
                    animation = tween(400 + (i % 5) * 60, easing = EaseInOut),
                    repeatMode = RepeatMode.Reverse,
                ),
                label = "bar$i",
            )
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .height(h.dp)
                    .background(Accent, RoundedCornerShape(1.dp)),
            )
        }
    }
}
