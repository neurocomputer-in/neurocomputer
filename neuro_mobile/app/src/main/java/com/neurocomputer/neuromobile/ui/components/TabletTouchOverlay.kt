package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import com.neurocomputer.neuromobile.data.service.LiveKitService
import kotlin.math.abs

/**
 * Full-screen transparent overlay converting touch gestures into absolute
 * (normalized) remote-input events on the LiveKit data channel.
 *
 * Pinch-zoom is applied locally via [onZoomChange] — never forwarded to PC
 * (desktop apps don't accept pinch). 2-finger pan → scroll wheel.
 */
@Composable
fun TabletTouchOverlay(
    liveKitService: LiveKitService,
    onZoomChange: (Float) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    var lastDragX by remember { mutableFloatStateOf(0f) }
    var lastDragY by remember { mutableFloatStateOf(0f) }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val widthPx = constraints.maxWidth.toFloat().coerceAtLeast(1f)
        val heightPx = constraints.maxHeight.toFloat().coerceAtLeast(1f)

        fun norm(x: Float, y: Float): Pair<Float, Float> =
            (x / widthPx).coerceIn(0f, 1f) to (y / heightPx).coerceIn(0f, 1f)

        androidx.compose.foundation.layout.Box(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            liveKitService.sendTouchEvent("touch_tap", nx, ny)
                        },
                        onLongPress = { offset ->
                            val (nx, ny) = norm(offset.x, offset.y)
                            liveKitService.sendTouchEvent("touch_long_press", nx, ny)
                        },
                    )
                }
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            lastDragX = offset.x
                            lastDragY = offset.y
                            val (nx, ny) = norm(offset.x, offset.y)
                            liveKitService.sendTouchEvent("touch_drag_start", nx, ny)
                        },
                        onDrag = { change, _ ->
                            lastDragX = change.position.x
                            lastDragY = change.position.y
                            val (nx, ny) = norm(change.position.x, change.position.y)
                            liveKitService.sendTouchEvent("touch_drag_move", nx, ny)
                        },
                        onDragEnd = {
                            val (nx, ny) = norm(lastDragX, lastDragY)
                            liveKitService.sendTouchEvent("touch_drag_end", nx, ny)
                        },
                    )
                }
                .pointerInput(Unit) {
                    detectTransformGestures { _, pan, gestureZoom, _ ->
                        if (abs(gestureZoom - 1f) > 0.005f) {
                            onZoomChange(gestureZoom)
                        } else {
                            // 2-finger pan → scroll wheel; dy sign matches natural wheel
                            val (nx, ny) = norm(widthPx / 2f, heightPx / 2f)
                            liveKitService.sendTouchEvent("scroll", nx, ny, dy = pan.y)
                        }
                    }
                }
        )
    }
}
