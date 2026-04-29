package com.neurocomputer.neuromobile.ui.apps.chat

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.domain.model.Message

private val PanelBg = Color(0xFF0a0a14)
private val CardBg = Color(0xFF0d1117)
private val UserCyan = Color(0xFF67e8f9)
private val AgentGreen = Color(0xFF86efac)
private val LiveRed = Color(0xFFef4444)
private val MutedText = Color(0xFF6b7280)

@Composable
fun VoiceCollapsedBar(
    isMuted: Boolean,
    onExpand: () -> Unit,
    onToggleMute: () -> Unit,
    onEndCall: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(Color(0xFF111118))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        // Live status capsule with pulsing dot + label
        Row(
            modifier = Modifier
                .background(Color(0xFF052e16), RoundedCornerShape(20.dp))
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            PulsingDot()
            Text(
                "On call",
                color = Color(0xFF86efac),
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }

        Spacer(Modifier.weight(1f))

        // Expand button — prominent rounded square with icon + subtle gradient
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(
                    Brush.linearGradient(
                        listOf(Color(0xFF2a1f4a), Color(0xFF1a1a2e)),
                    ),
                    RoundedCornerShape(11.dp),
                )
                .border(1.dp, Color(0xFF3a2f5a), RoundedCornerShape(11.dp)),
            contentAlignment = Alignment.Center,
        ) {
            IconButton(onClick = onExpand, modifier = Modifier.fillMaxSize()) {
                Icon(
                    Icons.Default.OpenInFull,
                    contentDescription = "Expand call",
                    tint = Color(0xFFc4b5fd),
                    modifier = Modifier.size(18.dp),
                )
            }
        }

        // Mute toggle
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(
                    if (isMuted) Color(0xFF3f1010) else Color(0xFF1f2937),
                    RoundedCornerShape(11.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            IconButton(onClick = onToggleMute, modifier = Modifier.fillMaxSize()) {
                Icon(
                    if (isMuted) Icons.Default.MicOff else Icons.Default.Mic,
                    contentDescription = if (isMuted) "Unmute" else "Mute",
                    tint = if (isMuted) LiveRed else Color.White,
                    modifier = Modifier.size(18.dp),
                )
            }
        }

        // End call
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(LiveRed, RoundedCornerShape(11.dp)),
            contentAlignment = Alignment.Center,
        ) {
            IconButton(onClick = onEndCall, modifier = Modifier.fillMaxSize()) {
                Icon(
                    Icons.Default.CallEnd,
                    contentDescription = "End call",
                    tint = Color.White,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
    }
}

@Composable
fun VoiceExpandedView(
    title: String,
    isMuted: Boolean,
    transcripts: List<Message>,
    interimUser: String,
    onCollapse: () -> Unit,
    onToggleMute: () -> Unit,
    onEndCall: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(PanelBg)
            .padding(16.dp),
    ) {
        // Header: title + LIVE badge
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    color = Color(0xFF8B5CF6),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text = "CONNECTED",
                    color = MutedText,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                )
            }
            // LIVE pill
            Row(
                modifier = Modifier
                    .border(1.dp, LiveRed.copy(alpha = 0.6f), RoundedCornerShape(6.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Box(Modifier.size(7.dp).background(LiveRed, CircleShape))
                Text("LIVE", color = LiveRed, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
            }
        }

        Spacer(Modifier.height(16.dp))

        // Terminal card
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(CardBg, RoundedCornerShape(12.dp))
                .border(1.dp, Color(0xFF1f2937), RoundedCornerShape(12.dp)),
        ) {
            Column(Modifier.fillMaxSize()) {
                // Card header — TRANSCRIPT label + traffic lights
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = ">_ TRANSCRIPT",
                        color = MutedText,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        letterSpacing = 1.sp,
                        modifier = Modifier.weight(1f),
                    )
                    Box(Modifier.size(9.dp).background(Color(0xFFFF5F57), CircleShape))
                    Spacer(Modifier.width(4.dp))
                    Box(Modifier.size(9.dp).background(Color(0xFFFFBD2E), CircleShape))
                    Spacer(Modifier.width(4.dp))
                    Box(Modifier.size(9.dp).background(Color(0xFF28CA41), CircleShape))
                }
                HorizontalDivider(color = Color(0xFF1f2937), thickness = 1.dp)

                // Transcript body
                if (transcripts.isEmpty() && interimUser.isEmpty()) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = "Listening…",
                            color = MutedText,
                            fontSize = 13.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                } else {
                    val listState = rememberLazyListState()
                    LaunchedEffect(transcripts.size, interimUser) {
                        val target = transcripts.size + if (interimUser.isNotEmpty()) 1 else 0
                        if (target > 0) listState.animateScrollToItem(target - 1)
                    }
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        items(transcripts) { msg -> TranscriptEntry(msg) }
                        if (interimUser.isNotEmpty()) {
                            item {
                                TranscriptEntry(
                                    Message(id = "interim", text = interimUser, isUser = true, isVoice = true),
                                    interim = true,
                                )
                            }
                        }
                    }
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Bottom controls — pill container
        Row(
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .background(CardBg, RoundedCornerShape(28.dp))
                .border(1.dp, Color(0xFF1f2937), RoundedCornerShape(28.dp))
                .padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            ControlButton(
                onClick = onToggleMute,
                bg = if (isMuted) Color(0xFF3f1010) else Color(0xFF1f2937),
                icon = if (isMuted) Icons.Default.MicOff else Icons.Default.Mic,
                tint = if (isMuted) LiveRed else Color.White,
                desc = if (isMuted) "Unmute" else "Mute",
            )
            ControlButton(
                onClick = onCollapse,
                bg = Color(0xFF1f2937),
                icon = Icons.Default.CloseFullscreen,
                tint = Color.White,
                desc = "Collapse",
            )
            ControlButton(
                onClick = onEndCall,
                bg = LiveRed,
                icon = Icons.Default.CallEnd,
                tint = Color.White,
                desc = "End call",
            )
        }
    }
}

@Composable
private fun TranscriptEntry(msg: Message, interim: Boolean = false) {
    Column(
        verticalArrangement = Arrangement.spacedBy(2.dp),
        modifier = Modifier.alpha(if (interim) 0.6f else 1f),
    ) {
        Text(
            text = if (msg.isUser) "you:~\$" else "neuro:~\$",
            color = if (msg.isUser) UserCyan else AgentGreen,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = msg.text,
            color = Color(0xFFe5e7eb),
            fontSize = 13.sp,
            fontFamily = FontFamily.Monospace,
        )
    }
}

@Composable
private fun ControlButton(
    onClick: () -> Unit,
    bg: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: Color,
    desc: String,
) {
    IconButton(
        onClick = onClick,
        modifier = Modifier.size(48.dp).background(bg, CircleShape),
    ) {
        Icon(icon, desc, tint = tint, modifier = Modifier.size(22.dp))
    }
}

@Composable
private fun PulsingDot() {
    val transition = rememberInfiniteTransition(label = "live-pulse")
    val alpha by transition.animateFloat(
        initialValue = 0.4f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(800, easing = EaseInOut), RepeatMode.Reverse),
        label = "alpha",
    )
    Box(
        Modifier
            .size(10.dp)
            .alpha(alpha)
            .background(Color(0xFF22c55e), CircleShape),
    )
}
