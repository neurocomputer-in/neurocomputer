package com.neurocomputer.neuromobile.ui.apps.terminal

import androidx.compose.ui.graphics.Color

data class AnsiSpan(val text: String, val color: Color? = null, val bold: Boolean = false)

object AnsiParser {

    private val ANSI_COLORS = mapOf(
        30 to Color(0xFF1a1a1a), 31 to Color(0xFFcc0000), 32 to Color(0xFF00aa00),
        33 to Color(0xFFaa8800), 34 to Color(0xFF0000cc), 35 to Color(0xFFaa00aa),
        36 to Color(0xFF00aaaa), 37 to Color(0xFFaaaaaa),
        90 to Color(0xFF555555), 91 to Color(0xFFff5555), 92 to Color(0xFF55ff55),
        93 to Color(0xFFffff55), 94 to Color(0xFF5555ff), 95 to Color(0xFFff55ff),
        96 to Color(0xFF55ffff), 97 to Color(0xFFffffff),
    )

    fun parse(input: String): List<AnsiSpan> {
        val spans = mutableListOf<AnsiSpan>()
        var currentColor: Color? = null
        var currentBold = false
        val regex = Regex("\u001B\\[([0-9;]*)m")
        var lastEnd = 0

        for (match in regex.findAll(input)) {
            val textBefore = input.substring(lastEnd, match.range.first)
            if (textBefore.isNotEmpty()) spans.add(AnsiSpan(textBefore, currentColor, currentBold))

            val codes = match.groupValues[1].split(";").mapNotNull { it.toIntOrNull() }
            for (code in codes) {
                when {
                    code == 0  -> { currentColor = null; currentBold = false }
                    code == 1  -> currentBold = true
                    code == 22 -> currentBold = false
                    ANSI_COLORS.containsKey(code) -> currentColor = ANSI_COLORS[code]
                }
            }
            lastEnd = match.range.last + 1
        }

        val remaining = input.substring(lastEnd)
        if (remaining.isNotEmpty()) spans.add(AnsiSpan(remaining, currentColor, currentBold))
        return spans
    }
}
