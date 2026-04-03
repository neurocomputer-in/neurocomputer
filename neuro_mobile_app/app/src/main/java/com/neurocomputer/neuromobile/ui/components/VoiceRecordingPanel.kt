package com.neurocomputer.neuromobile.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import kotlinx.coroutines.delay

@Composable
fun VoiceRecordingPanel(
    onDismiss: () -> Unit,
    onSend: () -> Unit
) {
    var isRecording by remember { mutableStateOf(false) }
    var recordingDuration by remember { mutableIntStateOf(0) }
    var waveformBars by remember { mutableStateOf(listOf(0.3f, 0.5f, 0.4f, 0.6f, 0.3f)) }

    val infiniteTransition = rememberInfiniteTransition(label = "waveform")

    // Launch timer when recording
    LaunchedEffect(isRecording) {
        if (isRecording) {
            while (true) {
                delay(1000)
                recordingDuration++
                waveformBars = waveformBars.map { (0.2f + Math.random().toFloat() * 0.8f) }
            }
        }
    }

    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
            .background(NeuroColors.BackgroundMid)
            .padding(24.dp)
            .padding(bottom = 32.dp)
    ) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .blur(15.dp)
                .background(NeuroColors.BackgroundMid.copy(alpha = 0.5f))
        ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth()
        ) {
            // Handle bar
            Box(
                modifier = Modifier
                    .width(40.dp)
                    .height(4.dp)
                    .background(NeuroColors.BorderLight, RoundedCornerShape(2.dp))
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Recording indicator
            if (isRecording) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .scale(pulseScale)
                            .background(Color(0xFFFF5555), CircleShape)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "Recording ${String.format("%02d:%02d", recordingDuration / 60, recordingDuration % 60)}",
                        color = NeuroColors.TextPrimary,
                        fontSize = 18.sp
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Waveform visualization
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    waveformBars.forEach { height ->
                        Box(
                            modifier = Modifier
                                .width(6.dp)
                                .height((40 * height).dp)
                                .background(NeuroColors.TextMuted, RoundedCornerShape(3.dp))
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))
            } else {
                Text(
                    text = "Tap to start recording",
                    color = NeuroColors.TextMuted,
                    fontSize = 14.sp
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Record button
                Box(
                    modifier = Modifier
                        .size(72.dp)
                        .clip(CircleShape)
                        .background(if (isRecording) Color(0xFFFF5555) else NeuroColors.GlassPrimary)
                        .then(
                            if (isRecording) Modifier else Modifier
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    IconButton(
                        onClick = {
                            isRecording = !isRecording
                            if (!isRecording) {
                                recordingDuration = 0
                            }
                        },
                        modifier = Modifier.size(72.dp)
                    ) {
                        Icon(
                            if (isRecording) Icons.Default.Stop else Icons.Default.Mic,
                            contentDescription = if (isRecording) "Stop" else "Record",
                            tint = NeuroColors.TextPrimary,
                            modifier = Modifier.size(32.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Action buttons
            Row(
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Cancel button
                OutlinedButton(
                    onClick = {
                        isRecording = false
                        recordingDuration = 0
                        onDismiss()
                    },
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = NeuroColors.TextMuted
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Close, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Cancel")
                }

                // Send button
                Button(
                    onClick = onSend,
                    enabled = recordingDuration > 0,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = NeuroColors.Primary,
                        contentColor = NeuroColors.BackgroundDark
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Send, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Send")
                }
            }
        }
        }
    }
}

@Composable
fun VoiceConnectingOverlay() {
    val infiniteTransition = rememberInfiniteTransition(label = "connecting")

    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(800),
            repeatMode = RepeatMode.Reverse
        ),
        label = "alpha"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NeuroColors.OverlayDark.copy(alpha = 0.5f)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(
                color = NeuroColors.Primary,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Connecting to voice...",
                color = NeuroColors.TextPrimary.copy(alpha = alpha),
                fontSize = 16.sp
            )
        }
    }
}

@Composable
fun VoiceConnectedOverlay(
    roomName: String,
    onDisconnect: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NeuroColors.OverlayDark.copy(alpha = 0.5f)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                Icons.Default.Headset,
                contentDescription = null,
                tint = NeuroColors.Primary,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Voice Connected",
                color = NeuroColors.TextPrimary,
                fontSize = 18.sp
            )
            Text(
                text = roomName,
                color = NeuroColors.TextMuted,
                fontSize = 12.sp
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onDisconnect,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFFFF5555),
                    contentColor = NeuroColors.TextPrimary
                )
            ) {
                Icon(Icons.Default.CallEnd, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Disconnect")
            }
        }
    }
}

@Composable
fun VoiceErrorOverlay(
    message: String,
    onRetry: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NeuroColors.OverlayDark.copy(alpha = 0.5f)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                Icons.Default.ErrorOutline,
                contentDescription = null,
                tint = Color(0xFFFF5555),
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Connection Error",
                color = NeuroColors.TextPrimary,
                fontSize = 18.sp
            )
            Text(
                text = message,
                color = NeuroColors.TextMuted,
                fontSize = 12.sp
            )
            Spacer(modifier = Modifier.height(24.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                OutlinedButton(
                    onClick = onRetry,
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = NeuroColors.TextPrimary
                    )
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Retry")
                }
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = NeuroColors.Primary,
                        contentColor = NeuroColors.BackgroundDark
                    )
                ) {
                    Text("Dismiss")
                }
            }
        }
    }
}
