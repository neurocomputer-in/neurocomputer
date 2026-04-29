package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ChevronHandle(onSwipeUp: () -> Unit, modifier: Modifier = Modifier) {
    var dragTotal by remember { mutableFloatStateOf(0f) }

    Box(
        modifier = modifier
            .height(24.dp)
            .background(Color.Transparent)
            .pointerInput(Unit) {
                detectVerticalDragGestures(
                    onDragStart = { dragTotal = 0f },
                    onDragEnd = { if (dragTotal < -60f) onSwipeUp(); dragTotal = 0f },
                    onVerticalDrag = { _, delta -> dragTotal += delta },
                )
            }
            .windowInsetsPadding(WindowInsets.navigationBars),
        contentAlignment = Alignment.Center,
    ) {
        Text("∧", color = Color(0xFF555566), fontSize = 10.sp)
    }
}
