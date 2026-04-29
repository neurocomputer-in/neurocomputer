package com.neurocomputer.neuromobile.ui.apps.desktop

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DesktopWindows
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.neurocomputer.neuromobile.domain.model.AgentType
import com.neurocomputer.neuromobile.ui.components.DraggableToolbarOverlay
import com.neurocomputer.neuromobile.ui.components.FullKeyboardOverlay
import com.neurocomputer.neuromobile.ui.components.TabletTouchOverlay
import com.neurocomputer.neuromobile.ui.components.TouchpadOverlay
import com.neurocomputer.neuromobile.ui.components.VoiceRecordingPanel

@Composable
fun DesktopApp(modifier: Modifier = Modifier) {
    val viewModel = hiltViewModel<MobileDesktopViewModel>()
    val state by viewModel.state.collectAsState()
    val videoTrack by viewModel.videoTrack.collectAsState()
    val serverCursor by viewModel.serverCursorPosition.collectAsState()
    val screenDims by viewModel.serverScreenDimensions.collectAsState()

    Box(modifier.fillMaxSize().background(Color.Black)) {
        // Video stream
        DesktopVideoView(videoTrack = videoTrack)

        // Server cursor dot
        ServerCursorOverlay(cursorPosition = serverCursor)

        if (state.isConnected) {
            // Touch input overlay
            if (state.isTabletMode) {
                TabletTouchOverlay(
                    liveKitService = viewModel.getLiveKitService(),
                    pcScreenWidth = screenDims.first,
                    pcScreenHeight = screenDims.second,
                    onLocalCursorChange = viewModel::setLocalCursor,
                )
            } else if (state.isTouchpadMode) {
                TouchpadOverlay(
                    isScrollMode = state.isScrollMode,
                    isClickMode = state.isClickMode,
                    isFocusMode = state.isFocusMode,
                    localCursor = state.localCursor,
                    pcScreenWidth = screenDims.first,
                    pcScreenHeight = screenDims.second,
                    onExit = {},
                    onLocalCursorChange = viewModel::setLocalCursor,
                    onDirectMove = viewModel::sendDirectMove,
                    onDirectClick = viewModel::sendDirectClick,
                    onMouseScroll = viewModel::sendMouseScroll,
                )
            }

            // Full keyboard overlay
            if (state.isKeyboardOpen) {
                FullKeyboardOverlay(
                    onKeyPress = viewModel::sendKeyEvent,
                    onComboPress = viewModel::sendKeyEvent,
                    onClose = viewModel::toggleKeyboard,
                )
            }

            // Voice typing panel
            if (state.isVoiceTyping) {
                Box(Modifier.align(Alignment.BottomCenter)) {
                    VoiceRecordingPanel(
                        onDismiss = viewModel::toggleVoiceTyping,
                        onSend = viewModel::toggleVoiceTyping,
                    )
                }
            }

            // Floating toolbar
            DraggableToolbarOverlay(
                offset = state.toolbarOffset,
                onOffsetChange = viewModel::setToolbarOffset,
                isVoiceTyping = state.isVoiceTyping,
                isKeyboardOpen = state.isKeyboardOpen,
                isScrollMode = state.isScrollMode,
                isClickMode = state.isClickMode,
                isFocusMode = state.isFocusMode,
                selectedAgentName = "Desktop",
                selectedAgentType = AgentType.NEURO,
                onVoiceTypeToggle = viewModel::toggleVoiceTyping,
                onSubmitVoice = viewModel::toggleVoiceTyping,
                onCancelVoice = viewModel::toggleVoiceTyping,
                onSendKey = viewModel::sendKeyEvent,
                onToggleKeyboard = viewModel::toggleKeyboard,
                onToggleScrollMode = viewModel::toggleScrollMode,
                onToggleClickMode = viewModel::toggleClickMode,
                onToggleFocusMode = viewModel::toggleFocusMode,
                onAgentClick = {},
            )
        } else {
            // Connect UI
            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.DesktopWindows,
                    contentDescription = null,
                    tint = Color(0xFF8B5CF6),
                    modifier = Modifier.size(64.dp),
                )
                Text("Remote Desktop", color = Color.White, fontSize = 20.sp)
                state.errorMessage?.let {
                    Text(it, color = Color(0xFFFF5555), fontSize = 13.sp)
                }
                Button(
                    onClick = viewModel::connect,
                    enabled = !state.isConnecting,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF8B5CF6)),
                ) {
                    if (state.isConnecting) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            color = Color.White,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(8.dp))
                    }
                    Text(if (state.isConnecting) "Connecting..." else "Connect to Desktop")
                }
            }
        }
    }
}

@Composable
private fun ServerCursorOverlay(cursorPosition: Offset?, modifier: Modifier = Modifier) {
    if (cursorPosition == null) return
    Canvas(modifier.fillMaxSize()) {
        val cx = cursorPosition.x * size.width
        val cy = cursorPosition.y * size.height
        drawCircle(color = Color(0xFFFF5555), radius = 6.dp.toPx(), center = Offset(cx, cy))
        drawCircle(color = Color.White, radius = 3.dp.toPx(), center = Offset(cx, cy))
    }
}
