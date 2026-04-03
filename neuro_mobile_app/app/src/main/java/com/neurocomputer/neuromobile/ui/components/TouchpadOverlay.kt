package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlin.math.abs

private const val MOVE_THRESHOLD = 3
private const val DOUBLE_TAP_INTERVAL = 300L
private const val MOVE_SENSITIVITY = 3.6f

/**
 * Transparent gesture-only touchpad overlay.
 * No visual chrome — the parent composable handles border indication.
 */
@Composable
fun TouchpadOverlay(
    isScrollMode: Boolean,
    isClickMode: Boolean,
    isFocusMode: Boolean,
    onExit: () -> Unit,
    onMouseMove: (Float, Float) -> Unit = { _, _ -> },
    onMouseClick: (Float, Float, String) -> Unit = { _, _, _ -> },
    onMouseScroll: (Float, Float) -> Unit = { _, _ -> }
) {
    var lastTouchX by remember { mutableFloatStateOf(0f) }
    var lastTouchY by remember { mutableFloatStateOf(0f) }
    var totalMovement by remember { mutableFloatStateOf(0f) }
    var isDragging by remember { mutableStateOf(false) }
    var lastTapTime by remember { mutableLongStateOf(0L) }

    BoxWithConstraints(
        modifier = Modifier.fillMaxSize()
    ) {
        val widthPx = constraints.maxWidth.toFloat()
        val heightPx = constraints.maxHeight.toFloat()

        Box(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { offset ->
                            val now = System.currentTimeMillis()
                            if (now - lastTapTime < DOUBLE_TAP_INTERVAL) {
                                onMouseClick(offset.x / widthPx, offset.y / heightPx, "left")
                                lastTapTime = 0L
                            } else {
                                lastTapTime = now
                            }
                        },
                        onLongPress = { offset ->
                            onMouseClick(offset.x / widthPx, offset.y / heightPx, "right")
                        }
                    )
                }
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            lastTouchX = offset.x
                            lastTouchY = offset.y
                            totalMovement = 0f
                            isDragging = false
                        },
                        onDrag = { change, _ ->
                            change.consume()
                            val dx = change.position.x - lastTouchX
                            val dy = change.position.y - lastTouchY
                            lastTouchX = change.position.x
                            lastTouchY = change.position.y
                            totalMovement += abs(dx) + abs(dy)

                            if (totalMovement > MOVE_THRESHOLD && !isDragging) {
                                isDragging = true
                            }

                            if (isDragging) {
                                if (isScrollMode) {
                                    onMouseScroll(dx, dy)
                                } else {
                                    onMouseMove(dx * MOVE_SENSITIVITY, dy * MOVE_SENSITIVITY)
                                }
                            }
                        },
                        onDragEnd = {
                            isDragging = false
                        }
                    )
                }
        )
    }
}
