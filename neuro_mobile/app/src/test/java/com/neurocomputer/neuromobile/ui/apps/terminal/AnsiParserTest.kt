package com.neurocomputer.neuromobile.ui.apps.terminal

import androidx.compose.ui.graphics.Color
import org.junit.Assert.*
import org.junit.Test

class AnsiParserTest {

    @Test fun `plain text returns single span with no color`() {
        val spans = AnsiParser.parse("hello world")
        assertEquals(1, spans.size)
        assertEquals("hello world", spans[0].text)
        assertNull(spans[0].color)
        assertFalse(spans[0].bold)
    }

    @Test fun `green text parsed correctly`() {
        val spans = AnsiParser.parse("\u001B[32mgreen\u001B[0m")
        assertEquals(1, spans.size)
        assertEquals("green", spans[0].text)
        assertEquals(Color(0xFF00aa00), spans[0].color)
    }

    @Test fun `bold text parsed`() {
        val spans = AnsiParser.parse("\u001B[1mbold\u001B[0m")
        assertEquals(1, spans.size)
        assertTrue(spans[0].bold)
    }

    @Test fun `reset clears color`() {
        val spans = AnsiParser.parse("\u001B[31mred\u001B[0m normal")
        assertEquals(2, spans.size)
        assertNotNull(spans[0].color)
        assertNull(spans[1].color)
    }

    @Test fun `unknown escape code stripped`() {
        val spans = AnsiParser.parse("\u001B[99munknown\u001B[0m")
        assertEquals(1, spans.size)
        assertEquals("unknown", spans[0].text)
    }
}
