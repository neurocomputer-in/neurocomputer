package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Backspace
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

data class KeyDef(val label: String, val key: String)

val KEYBOARD_ROWS = listOf(
    listOf(
        KeyDef("Esc", "Escape"), KeyDef("F1", "F1"), KeyDef("F2", "F2"), KeyDef("F3", "F3"),
        KeyDef("F4", "F4"), KeyDef("F5", "F5"), KeyDef("F6", "F6"), KeyDef("F7", "F7"),
        KeyDef("F8", "F8"), KeyDef("F9", "F9"), KeyDef("F10", "F10"), KeyDef("F11", "F11"),
        KeyDef("F12", "F12"), KeyDef("⌫", "BackSpace")
    ),
    listOf(
        KeyDef("`", "grave"), KeyDef("1", "1"), KeyDef("2", "2"), KeyDef("3", "3"),
        KeyDef("4", "4"), KeyDef("5", "5"), KeyDef("6", "6"), KeyDef("7", "7"),
        KeyDef("8", "8"), KeyDef("9", "9"), KeyDef("0", "0"), KeyDef("-", "minus"),
        KeyDef("=", "equal")
    ),
    listOf(
        KeyDef("Tab", "Tab"), KeyDef("Q", "q"), KeyDef("W", "w"), KeyDef("E", "e"),
        KeyDef("R", "r"), KeyDef("T", "t"), KeyDef("Y", "y"), KeyDef("U", "u"),
        KeyDef("I", "i"), KeyDef("O", "o"), KeyDef("P", "p"), KeyDef("[", "bracketleft"),
        KeyDef("]", "bracketright"), KeyDef("\\", "backslash")
    ),
    listOf(
        KeyDef("Caps", "CapsLock"), KeyDef("A", "a"), KeyDef("S", "s"), KeyDef("D", "d"),
        KeyDef("F", "f"), KeyDef("G", "g"), KeyDef("H", "h"), KeyDef("J", "j"),
        KeyDef("K", "k"), KeyDef("L", "l"), KeyDef(";", "semicolon"), KeyDef("'", "apostrophe"),
        KeyDef("Enter", "Return")
    ),
    listOf(
        KeyDef("Shift", "LShift"), KeyDef("Z", "z"), KeyDef("X", "x"), KeyDef("C", "c"),
        KeyDef("V", "v"), KeyDef("B", "b"), KeyDef("N", "n"), KeyDef("M", "m"),
        KeyDef(",", "comma"), KeyDef(".", "period"), KeyDef("/", "slash"), KeyDef("Shift", "RShift")
    ),
    listOf(
        KeyDef("Ctrl", "LCtrl"), KeyDef("Alt", "LAlt"), KeyDef("Space", "space"),
        KeyDef("Alt", "RAlt"), KeyDef("Ctrl", "RCtrl"), KeyDef("←", "Left"),
        KeyDef("↑", "Up"), KeyDef("↓", "Down"), KeyDef("→", "Right")
    )
)

val MODIFIER_KEYS = setOf("LShift", "RShift", "LCtrl", "RCtrl", "LAlt", "RAlt", "CapsLock", "Tab", "space")

@Composable
fun FullKeyboardOverlay(
    onKeyPress: (String) -> Unit,
    onComboPress: (String) -> Unit,
    onClose: () -> Unit
) {
    var shiftActive by remember { mutableStateOf(false) }
    var ctrlActive by remember { mutableStateOf(false) }
    var altActive by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.15f))
            .zIndex(9999f)
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .padding(bottom = 32.dp),
            contentPadding = PaddingValues(horizontal = 8.dp)
        ) {
            itemsIndexed(KEYBOARD_ROWS) { _, row ->
                Row(modifier = Modifier.fillMaxWidth()) {
                    row.forEach { keyDef ->
                        KeyboardKey(
                            keyDef = keyDef,
                            isModifierActive = when (keyDef.key) {
                                "LShift", "RShift" -> shiftActive
                                "LCtrl", "RCtrl" -> ctrlActive
                                "LAlt", "RAlt" -> altActive
                                else -> false
                            },
                            modifier = Modifier.weight(if (keyDef.key == "space") 2f else 1f),
                            onClick = {
                                when (keyDef.key) {
                                    "LShift", "RShift" -> {
                                        shiftActive = !shiftActive
                                    }
                                    "LCtrl", "RCtrl" -> {
                                        ctrlActive = !ctrlActive
                                    }
                                    "LAlt", "RAlt" -> {
                                        altActive = !altActive
                                    }
                                    "CapsLock" -> {
                                        shiftActive = !shiftActive
                                        onKeyPress("Caps_Lock")
                                    }
                                    "space" -> {
                                        if (ctrlActive) {
                                            onComboPress("ctrl+space")
                                            ctrlActive = false
                                        } else if (altActive) {
                                            onComboPress("alt+space")
                                            altActive = false
                                        } else {
                                            onKeyPress("space")
                                        }
                                    }
                                    else -> {
                                        val parts = mutableListOf<String>()
                                        if (ctrlActive) parts.add("ctrl")
                                        if (altActive) parts.add("alt")
                                        if (shiftActive && keyDef.key.length == 1) parts.add("shift")
                                        parts.add(keyDef.key)

                                        if (parts.size > 1) {
                                            onComboPress(parts.joinToString("+"))
                                        } else {
                                            onKeyPress(
                                                if (shiftActive && keyDef.key.length == 1)
                                                    keyDef.key.uppercase()
                                                else keyDef.key
                                            )
                                        }

                                        if (ctrlActive || altActive) {
                                            ctrlActive = false
                                            altActive = false
                                        }
                                    }
                                }
                            }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(2.dp))
            }
        }

        // Close button
        IconButton(
            onClick = onClose,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(16.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(Color(0x40FF5555))
        ) {
            Icon(
                Icons.Default.Close,
                contentDescription = "Close Keyboard",
                tint = Color(0xFFFF7878)
            )
        }

        // Modifier status
        Row(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(16.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color.Black.copy(alpha = 0.4f))
                .padding(horizontal = 12.dp, vertical = 6.dp)
        ) {
            if (ctrlActive) Text("Ctrl ", color = Color(0xFF8BE9FD), fontSize = 12.sp)
            if (altActive) Text("Alt ", color = Color(0xFF8BE9FD), fontSize = 12.sp)
            if (shiftActive) Text("Shift ", color = Color(0xFFF1FA8C), fontSize = 12.sp)
        }
    }
}

@Composable
fun KeyboardKey(
    keyDef: KeyDef,
    isModifierActive: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val backgroundColor = when {
        isModifierActive -> Color(0x738B5CF6)
        MODIFIER_KEYS.contains(keyDef.key) -> NeuroColors.GlassPrimary
        else -> NeuroColors.GlassSecondary
    }

    val borderColor = when {
        isModifierActive -> Color(0xCC8B5CF6)
        MODIFIER_KEYS.contains(keyDef.key) -> NeuroColors.BorderLight
        else -> NeuroColors.BorderSubtle
    }

    val textColor = when {
        isModifierActive -> Color.White
        MODIFIER_KEYS.contains(keyDef.key) -> NeuroColors.TextSecondary
        else -> NeuroColors.TextPrimary.copy(alpha = 0.65f)
    }

    Box(
        modifier = modifier
            .height(48.dp)
            .padding(1.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(backgroundColor)
            .border(1.dp, borderColor, RoundedCornerShape(6.dp))
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = keyDef.label,
            color = textColor,
            fontSize = if (keyDef.label.length > 3) 9.sp else 12.sp,
            textAlign = TextAlign.Center
        )
    }
}
