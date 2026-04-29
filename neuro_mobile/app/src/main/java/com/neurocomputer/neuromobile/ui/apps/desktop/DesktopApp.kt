package com.neurocomputer.neuromobile.ui.apps.desktop

import android.app.Activity
import android.content.pm.ActivityInfo
import android.view.WindowManager
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.DesktopWindows
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import kotlin.math.roundToInt
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
    val room by viewModel.currentRoom.collectAsState()
    val serverCursor by viewModel.serverCursorPosition.collectAsState()
    val screenDims by viewModel.serverScreenDimensions.collectAsState()

    val view = LocalView.current
    DisposableEffect(state.isConnected) {
        val activity = view.context as? Activity
        val window = activity?.window
        // Desktop streams 1280×720 — letterboxed in portrait. While connected
        // we lock landscape so the video can fill the screen and the touchpad
        // gets a sensible aspect ratio. Restore on disconnect so home/chat
        // tabs go back to the user's preferred orientation.
        val previousOrientation = activity?.requestedOrientation
        val insetsController = window?.let { WindowInsetsControllerCompat(it, view) }
        if (state.isConnected) {
            window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            // Hide status + nav bars; sticky behavior keeps them hidden after
            // a swipe-to-reveal gesture (system shows them briefly, then auto-
            // hides again). Required for a proper fullscreen kiosk feel.
            insetsController?.systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            insetsController?.hide(WindowInsetsCompat.Type.systemBars())
        }
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            if (previousOrientation != null) {
                activity?.requestedOrientation = previousOrientation
            } else {
                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            }
            insetsController?.show(WindowInsetsCompat.Type.systemBars())
        }
    }

    Box(modifier.fillMaxSize().background(Color.Black)) {
        // Video stream
        DesktopVideoView(room = room, videoTrack = videoTrack)

        // Server cursor dot
        ServerCursorOverlay(cursorPosition = serverCursor)

        // Pulsing inset border — visual cue that the desktop tab is "live"
        // and which input mode is active. Below the touch overlays so it
        // doesn't intercept input.
        if (state.isConnected) {
            GlowingBorder(
                isTouchpadMode = state.isTouchpadMode,
                isTabletMode = state.isTabletMode,
                connected = true,
            )
        }

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

            // Collapsible left-edge toolbar. Default state: small chevron tab
            // pinned to the screen edge; tapping expands to the full pill of
            // controls. Position is locked to x = 0; user can drag vertically
            // to reposition.
            CollapsibleLeftToolbar(
                verticalOffset = state.toolbarOffset.y,
                onVerticalOffsetChange = { viewModel.setToolbarOffset(Offset(0f, it)) },
            ) { onCollapse ->
                DraggableToolbarOverlay(
                    // Pin x to 0 so the pill is flush with the left edge. y
                    // is owned by the wrapper; we feed it through unchanged.
                    offset = Offset(0f, 0f),
                    onOffsetChange = { /* drag handled by wrapper */ },
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
                    onAgentClick = onCollapse,
                    showAgentButton = false,
                    isTouchpadMode = state.isTouchpadMode,
                    isTabletMode = state.isTabletMode,
                    onToggleTouchpadMode = viewModel::toggleTouchpadMode,
                    onToggleTabletMode = viewModel::toggleTabletMode,
                    onDisconnect = viewModel::disconnect,
                )
            }
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

/**
 * Default-collapsed toolbar pinned to the left screen edge. When collapsed it
 * shows a thin pull-tab; tapping expands the supplied pill content (the full
 * `DraggableToolbarOverlay`). Drag handle on the tab and on the expanded
 * pill's "agent button" slot let the user reposition vertically without
 * losing the left-edge anchor.
 */
@Composable
private fun CollapsibleLeftToolbar(
    verticalOffset: Float,
    onVerticalOffsetChange: (Float) -> Unit,
    content: @Composable (onCollapse: () -> Unit) -> Unit,
) {
    var collapsed by remember { mutableStateOf(true) }

    Box(
        modifier = Modifier
            .offset { IntOffset(0, verticalOffset.roundToInt()) }
            .zIndex(9999f)
            .pointerInput(Unit) {
                detectDragGestures { change, drag ->
                    change.consume()
                    onVerticalOffsetChange(
                        (verticalOffset + drag.y).coerceIn(0f, 2000f)
                    )
                }
            },
    ) {
        if (collapsed) {
            // Slim pull tab — tap to expand.
            Box(
                modifier = Modifier
                    .size(width = 24.dp, height = 60.dp)
                    .background(
                        Color(0xCC1a1a24),
                        RoundedCornerShape(topEnd = 12.dp, bottomEnd = 12.dp),
                    )
                    .clickable { collapsed = false },
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Default.ChevronRight,
                    contentDescription = "Open toolbar",
                    tint = Color(0xFFcfd6e3),
                    modifier = Modifier.size(18.dp),
                )
            }
        } else {
            Column(horizontalAlignment = Alignment.Start) {
                // Header strip with collapse arrow
                Box(
                    modifier = Modifier
                        .background(
                            Color(0xCC1a1a24),
                            RoundedCornerShape(topEnd = 12.dp, bottomEnd = 12.dp),
                        )
                        .clickable { collapsed = true }
                        .padding(horizontal = 6.dp, vertical = 4.dp),
                ) {
                    Icon(
                        Icons.Default.ChevronLeft,
                        contentDescription = "Collapse toolbar",
                        tint = Color(0xFFcfd6e3),
                        modifier = Modifier.size(18.dp),
                    )
                }
                Spacer(Modifier.height(4.dp))
                content { collapsed = true }
            }
        }
    }
}
