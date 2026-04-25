package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import kotlinx.coroutines.delay
import kotlin.math.abs
import kotlin.math.sqrt
import kotlin.math.pow

private const val MOVE_THRESHOLD = 3
private const val DOUBLE_TAP_INTERVAL = 350L
private const val TAP_CONFIRM_DELAY = 180L
private const val BASE_SENSITIVITY = 1.0f
private const val ACCEL_FACTOR = 0.18f
private const val ACCEL_POWER = 0.65f
private const val MAX_SENSITIVITY = 12.0f
private const val PC_SENS = 2.5f

/**
 * Touchpad-style overlay. Phone owns the cursor (zero-latency arrow) and sends
 * absolute direct_move events so the PC follows.
 *
 * Gesture map:
 *  - Single tap            → left click at cursor pos
 *  - Double-tap            → double-click at cursor pos
 *  - Long press            → right click at cursor pos
 *  - Double-tap-then-drag  → mousedown, move, mouseup  (text selection, drag-drop)
 *  - Single drag           → move cursor
 *  - Scroll mode drag      → scroll wheel
 */
@Composable
fun TouchpadOverlay(
    isScrollMode: Boolean,
    isClickMode: Boolean,
    isFocusMode: Boolean,
    localCursor: Offset,
    pcScreenWidth: Int,
    pcScreenHeight: Int,
    onExit: () -> Unit,
    onLocalCursorChange: (Offset) -> Unit = {},
    onDirectMove: (Float, Float) -> Unit = { _, _ -> },
    onDirectClick: (Float, Float, String, Int) -> Unit = { _, _, _, _ -> },
    onMouseScroll: (Float, Float) -> Unit = { _, _ -> },
    onMouseDown: (() -> Unit)? = null,
    onMouseUp: (() -> Unit)? = null,
) {
    val cursorRef = rememberUpdatedState(localCursor)

    // Pointer-DOWN counter — updated on each press, before tap/drag disambiguates.
    // This lets onDragStart know how many recent presses preceded the drag.
    var pointerDownCount by remember { mutableIntStateOf(0) }
    var lastDownTime by remember { mutableLongStateOf(0L) }

    // Tap state (fires on pointer UP via detectTapGestures)
    var tapCount by remember { mutableIntStateOf(0) }
    var lastTapTime by remember { mutableLongStateOf(0L) }
    var pendingClickCount by remember { mutableIntStateOf(0) }
    var hasPendingClick by remember { mutableStateOf(false) }

    // Drag state
    var lastTouchX by remember { mutableFloatStateOf(0f) }
    var lastTouchY by remember { mutableFloatStateOf(0f) }
    var totalMovement by remember { mutableFloatStateOf(0f) }
    var isDragging by remember { mutableStateOf(false) }
    var isDragMode by remember { mutableStateOf(false) }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val phoneW = constraints.maxWidth.toFloat().coerceAtLeast(1f)
        val phoneH = constraints.maxHeight.toFloat().coerceAtLeast(1f)
        val pcW = pcScreenWidth.coerceAtLeast(1).toFloat()
        val pcH = pcScreenHeight.coerceAtLeast(1).toFloat()

        val pcAspect = pcW / pcH
        val phoneAspect = phoneW / phoneH
        val renderW: Float
        val renderH: Float
        if (phoneAspect > pcAspect) {
            renderH = phoneH; renderW = phoneH * pcAspect
        } else {
            renderW = phoneW; renderH = phoneW / pcAspect
        }

        Box(
            modifier = Modifier
                .fillMaxSize()
                // Layer 1: count pointer DOWNs before tap/drag disambiguates
                .pointerInput(Unit) {
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        val now = System.currentTimeMillis()
                        if (now - lastDownTime < DOUBLE_TAP_INTERVAL) {
                            pointerDownCount++
                        } else {
                            pointerDownCount = 1
                        }
                        lastDownTime = now
                        waitForUpOrCancellation()  // wait without consuming
                    }
                }
                // Layer 2: tap / long-press recognition (no onDoubleTap — fires onTap immediately)
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = {
                            val now = System.currentTimeMillis()
                            if (now - lastTapTime < DOUBLE_TAP_INTERVAL) {
                                tapCount++
                            } else {
                                tapCount = 1
                            }
                            lastTapTime = now
                            pendingClickCount = tapCount
                            hasPendingClick = true
                        },
                        onLongPress = {
                            val c = cursorRef.value
                            onDirectClick(c.x, c.y, "right", 1)
                            tapCount = 0
                            hasPendingClick = false
                        }
                    )
                }
                // Layer 3: drag / scroll / drag-mode
                .pointerInput(isScrollMode) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            lastTouchX = offset.x
                            lastTouchY = offset.y
                            totalMovement = 0f
                            isDragging = false

                            // Use pointer-DOWN count (tracked before drag disambiguates)
                            val now = System.currentTimeMillis()
                            val recentDown = (now - lastDownTime) < DOUBLE_TAP_INTERVAL
                            isDragMode = recentDown && pointerDownCount >= 2
                            if (isDragMode) onMouseDown?.invoke()

                            pointerDownCount = 0
                            lastDownTime = 0L
                            hasPendingClick = false
                            tapCount = 0
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
                                if (isScrollMode && !isDragMode) {
                                    onMouseScroll(dx, dy)
                                } else {
                                    val speed = sqrt(dx * dx + dy * dy)
                                    val sens = (BASE_SENSITIVITY +
                                        ACCEL_FACTOR * speed.pow(ACCEL_POWER))
                                        .coerceAtMost(MAX_SENSITIVITY)
                                    val ndx = (dx * sens * PC_SENS) / renderW
                                    val ndy = (dy * sens * PC_SENS) / renderH
                                    val c = cursorRef.value
                                    val nx = (c.x + ndx).coerceIn(0f, 1f)
                                    val ny = (c.y + ndy).coerceIn(0f, 1f)
                                    onLocalCursorChange(Offset(nx, ny))
                                    onDirectMove(nx, ny)
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

        // Delayed tap → fire click after double-tap disambiguation window
        LaunchedEffect(hasPendingClick, pendingClickCount) {
            if (hasPendingClick) {
                delay(TAP_CONFIRM_DELAY)
                if (hasPendingClick) {
                    val count = pendingClickCount.coerceIn(1, 2)
                    val c = cursorRef.value
                    onDirectClick(c.x, c.y, "left", count)
                    hasPendingClick = false
                    tapCount = 0
                }
            }
        }
    }
}
