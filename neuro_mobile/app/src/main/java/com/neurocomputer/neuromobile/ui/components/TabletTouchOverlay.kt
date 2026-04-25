package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import com.neurocomputer.neuromobile.data.service.LiveKitService
import kotlin.math.abs

/**
 * Full-screen transparent overlay converting touch gestures into absolute
 * (normalized) remote-input events on the LiveKit data channel.
 *
 * Coordinate mapping accounts for the FitInside letterbox/pillarbox so that
 * tapping a pixel on the phone matches exactly that pixel on the PC desktop.
 * The local cursor position is emitted via [onLocalCursorChange] for zero-
 * latency arrow rendering on-device.
 */
@Composable
fun TabletTouchOverlay(
    liveKitService: LiveKitService,
    pcScreenWidth: Int = 1920,
    pcScreenHeight: Int = 1080,
    onZoomChange: (Float) -> Unit = {},
    onLocalCursorChange: (Offset) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    var lastDragNx by remember { mutableFloatStateOf(0f) }
    var lastDragNy by remember { mutableFloatStateOf(0f) }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val phoneW = constraints.maxWidth.toFloat().coerceAtLeast(1f)
        val phoneH = constraints.maxHeight.toFloat().coerceAtLeast(1f)

        // Compute the FitInside video render rectangle on the phone screen.
        val pcAspect = if (pcScreenHeight > 0) pcScreenWidth.toFloat() / pcScreenHeight else 16f / 9f
        val phoneAspect = phoneW / phoneH
        val renderW: Float
        val renderH: Float
        if (phoneAspect > pcAspect) {
            // Phone wider than video → pillarbox
            renderH = phoneH
            renderW = phoneH * pcAspect
        } else {
            // Phone taller than video → letterbox
            renderW = phoneW
            renderH = phoneW / pcAspect
        }
        val offsetX = (phoneW - renderW) / 2f
        val offsetY = (phoneH - renderH) / 2f

        /** Map raw phone-pixel (x, y) → PC-normalized (0..1, 0..1). */
        fun norm(x: Float, y: Float): Pair<Float, Float> =
            ((x - offsetX) / renderW).coerceIn(0f, 1f) to
            ((y - offsetY) / renderH).coerceIn(0f, 1f)

        androidx.compose.foundation.layout.Box(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            onLocalCursorChange(Offset(nx, ny))
                            liveKitService.sendTouchEvent("touch_tap", nx, ny)
                        },
                        onDoubleTap = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            onLocalCursorChange(Offset(nx, ny))
                            liveKitService.sendTouchEvent("touch_tap", nx, ny, count = 2)
                        },
                        onLongPress = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            onLocalCursorChange(Offset(nx, ny))
                            liveKitService.sendTouchEvent("touch_long_press", nx, ny)
                        },
                    )
                }
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            lastDragNx = nx
                            lastDragNy = ny
                            onLocalCursorChange(Offset(nx, ny))
                            liveKitService.sendTouchEvent("touch_drag_start", nx, ny)
                        },
                        onDrag = { change, _ ->
                            val (nx, ny) = norm(change.position.x, change.position.y)
                            lastDragNx = nx
                            lastDragNy = ny
                            onLocalCursorChange(Offset(nx, ny))
                            liveKitService.sendTouchEvent("touch_drag_move", nx, ny)
                        },
                        onDragEnd = {
                            onLocalCursorChange(Offset(lastDragNx, lastDragNy))
                            liveKitService.sendTouchEvent("touch_drag_end", lastDragNx, lastDragNy)
                        },
                    )
                }
                .pointerInput(Unit) {
                    detectTransformGestures { _, pan, gestureZoom, _ ->
                        if (abs(gestureZoom - 1f) > 0.005f) {
                            onZoomChange(gestureZoom)
                        } else {
                            val cx = (phoneW / 2f - offsetX) / renderW
                            val cy = (phoneH / 2f - offsetY) / renderH
                            liveKitService.sendTouchEvent("scroll", cx.coerceIn(0f, 1f), cy.coerceIn(0f, 1f), dy = pan.y)
                        }
                    }
                }
        )
    }
}
