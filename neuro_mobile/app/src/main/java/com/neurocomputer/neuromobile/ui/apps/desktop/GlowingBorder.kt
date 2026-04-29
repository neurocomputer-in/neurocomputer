package com.neurocomputer.neuromobile.ui.apps.desktop

import androidx.compose.animation.core.EaseInOut
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

/**
 * Inset border that pulses while connected — matches the web GlowingBorder.
 * Color reflects the active touch mode so the user knows what input mapping
 * is live (touchpad / tablet / display-only).
 */
@Composable
fun GlowingBorder(
    isTouchpadMode: Boolean,
    isTabletMode: Boolean,
    connected: Boolean,
    modifier: Modifier = Modifier,
) {
    val color = when {
        isTabletMode -> Color(0xFF6366F1)   // indigo-500
        isTouchpadMode -> Color(0xFF06B6D4) // cyan-500
        else -> Color(0xFF71717A)            // zinc-500 (display-only)
    }

    val transition = rememberInfiniteTransition(label = "glow")
    val pulseAlpha by transition.animateFloat(
        initialValue = if (connected) 0.4f else 0.15f,
        targetValue = if (connected) 0.7f else 0.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = EaseInOut),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "pulseAlpha",
    )

    Canvas(modifier = modifier.fillMaxSize()) {
        // 2dp inset border. Stroke is centered on the path so we offset the
        // rect inward by half-width to keep it fully visible at the edge.
        val strokeWidth = 2.dp.toPx()
        val half = strokeWidth / 2f
        drawRect(
            color = color.copy(alpha = pulseAlpha),
            topLeft = Offset(half, half),
            size = Size(size.width - strokeWidth, size.height - strokeWidth),
            style = Stroke(width = strokeWidth),
        )
    }
}
