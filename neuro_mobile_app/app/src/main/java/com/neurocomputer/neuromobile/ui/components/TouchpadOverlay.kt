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
import kotlin.math.sqrt
import kotlin.math.pow

private const val MOVE_THRESHOLD = 3
private const val TAP_INTERVAL = 300L
private const val TRIPLE_TAP_COUNT = 3
private const val TAP_CONFIRM_DELAY = 200L
private const val BASE_SENSITIVITY = 1.0f
private const val ACCEL_FACTOR = 0.18f
private const val ACCEL_POWER = 0.65f
private const val MAX_SENSITIVITY = 12.0f

@Composable
fun TouchpadOverlay(
    isScrollMode: Boolean,
    isClickMode: Boolean,
    isFocusMode: Boolean,
    onExit: () -> Unit,
    onMouseMove: (Float, Float) -> Unit = { _, _ -> },
    onMouseClick: (Float, Float, String) -> Unit = { _, _, _ -> },
    onMouseScroll: (Float, Float) -> Unit = { _, _ -> },
    onMouseDown: (() -> Unit)? = null,
    onMouseUp: (() -> Unit)? = null
) {
    var lastTouchX by remember { mutableFloatStateOf(0f) }
    var lastTouchY by remember { mutableFloatStateOf(0f) }
    var totalMovement by remember { mutableFloatStateOf(0f) }
    var isDragging by remember { mutableStateOf(false) }
    var isDragMode by remember { mutableStateOf(false) }

    var tapCount by remember { mutableIntStateOf(0) }
    var lastTapTime by remember { mutableLongStateOf(0L) }
    var pendingClickX by remember { mutableFloatStateOf(0f) }
    var pendingClickY by remember { mutableFloatStateOf(0f) }
    var hasPendingClick by remember { mutableStateOf(false) }

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
                            if (now - lastTapTime < TAP_INTERVAL) {
                                tapCount++
                            } else {
                                tapCount = 1
                            }
                            lastTapTime = now
                            pendingClickX = offset.x
                            pendingClickY = offset.y
                            hasPendingClick = true
                        },
                        onLongPress = { offset ->
                            onMouseClick(offset.x / widthPx, offset.y / heightPx, "right")
                        }
                    )
                }
                .pointerInput(isScrollMode) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            lastTouchX = offset.x
                            lastTouchY = offset.y
                            totalMovement = 0f
                            isDragging = false

                            val now = System.currentTimeMillis()
                            val recentTap = (now - lastTapTime) < TAP_INTERVAL
                            isDragMode = recentTap && tapCount >= TRIPLE_TAP_COUNT
                            if (isDragMode) {
                                onMouseDown?.invoke()
                            }
                            tapCount = 0
                            lastTapTime = 0L
                            hasPendingClick = false
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
                                hasPendingClick = false
                                if (isScrollMode && !isDragMode) {
                                    onMouseScroll(dx, dy)
                                } else {
                                    val speed = sqrt(dx * dx + dy * dy)
                                    val sensitivity = (BASE_SENSITIVITY +
                                        ACCEL_FACTOR * speed.pow(ACCEL_POWER))
                                        .coerceAtMost(MAX_SENSITIVITY)
                                    onMouseMove(dx * sensitivity, dy * sensitivity)
                                }
                            }
                        },
                        onDragEnd = {
                            if (isDragMode) {
                                onMouseUp?.invoke()
                                isDragMode = false
                            }
                            isDragging = false
                        }
                    )
                }
        )

        LaunchedEffect(hasPendingClick, tapCount) {
            if (hasPendingClick && tapCount < TRIPLE_TAP_COUNT) {
                delay(TAP_CONFIRM_DELAY)
                if (hasPendingClick && tapCount < TRIPLE_TAP_COUNT) {
                    onMouseClick(pendingClickX / widthPx, pendingClickY / heightPx, "left")
                    hasPendingClick = false
                }
            }
        }
    }
}