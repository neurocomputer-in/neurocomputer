package com.neurocomputer.neuromobile.ui.apps.terminal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun TerminalOutputView(
    lines: List<List<AnsiSpan>>,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()
    LaunchedEffect(lines.size) {
        if (lines.isNotEmpty()) listState.animateScrollToItem(lines.size - 1)
    }
    LazyColumn(
        state = listState,
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
    ) {
        items(lines, key = { it.hashCode() }) { spans ->
            val annotated = buildAnnotatedString {
                spans.forEach { span ->
                    pushStyle(SpanStyle(
                        color = span.color ?: Color(0xFFcccccc),
                        fontWeight = if (span.bold) FontWeight.Bold else FontWeight.Normal,
                    ))
                    append(span.text)
                    pop()
                }
            }
            Text(text = annotated, fontSize = 12.sp, lineHeight = 16.sp, fontFamily = FontFamily.Monospace)
        }
    }
}
