package com.neurocomputer.neuromobile.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
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

private val KeyboardBg = Color(0xFF0F1020)
private val KeyBg = Color(0xFF1E2038)
private val KeyBgModifier = Color(0xFF2A2060)
private val KeyBgActive = Color(0xFF5B3FA0)
private val KeyBorder = Color(0xFF3A3D5C)
private val KeyBorderActive = Color(0xFF8B5CF6)

@Composable
fun FullKeyboardOverlay(
    onKeyPress: (String) -> Unit,
    onComboPress: (String) -> Unit,
    onClose: () -> Unit,
    startPadding: Dp = 0.dp,
) {
    var shiftActive by remember { mutableStateOf(false) }
    var ctrlActive by remember { mutableStateOf(false) }
    var altActive by remember { mutableStateOf(false) }
    var lastKey by remember { mutableStateOf("") }

    // No full-screen scrim — keyboard is self-contained at bottom
    Box(
        modifier = Modifier
            .fillMaxSize()
            .zIndex(9999f)
            .padding(start = startPadding)
    ) {
        // Keyboard container — anchored at bottom with its own opaque background
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .clip(RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp))
                .background(KeyboardBg)
                .border(
                    width = 1.dp,
                    color = Color(0xFF4A4D70),
                    shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp)
                )
                .padding(top = 6.dp, bottom = 12.dp)
        ) {
            // Top bar: last-pressed key indicator + close button
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 10.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Modifier pills
                Row(
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    if (ctrlActive) ModifierPill("Ctrl", Color(0xFF8BE9FD))
                    if (altActive) ModifierPill("Alt", Color(0xFFFFB86C))
                    if (shiftActive) ModifierPill("Shift", Color(0xFFF1FA8C))
                }

                // Last-pressed key badge
                if (lastKey.isNotEmpty()) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(Color(0xFF2A2D4A))
                            .border(1.dp, Color(0xFF6C6FA8), RoundedCornerShape(6.dp))
                            .padding(horizontal = 10.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = lastKey,
                            color = Color.White,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                }

                // Close button
                IconButton(
                    onClick = onClose,
                    modifier = Modifier
                        .size(28.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF2A1A1A))
                        .border(1.dp, Color(0xFF5A2020), RoundedCornerShape(8.dp))
                ) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "Close Keyboard",
                        tint = Color(0xFFFF7878),
                        modifier = Modifier.size(16.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(2.dp))

            // Key rows
            KEYBOARD_ROWS.forEach { row ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 6.dp),
                ) {
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
                                    "LShift", "RShift" -> shiftActive = !shiftActive
                                    "LCtrl", "RCtrl" -> ctrlActive = !ctrlActive
                                    "LAlt", "RAlt" -> altActive = !altActive
                                    "CapsLock" -> {
                                        shiftActive = !shiftActive
                                        onKeyPress("Caps_Lock")
                                        lastKey = "Caps"
                                    }
                                    "space" -> {
                                        val combo = buildList {
                                            if (ctrlActive) add("ctrl")
                                            if (altActive) add("alt")
                                            add("space")
                                        }
                                        if (combo.size > 1) {
                                            onComboPress(combo.joinToString("+"))
                                        } else {
                                            onKeyPress("space")
                                        }
                                        ctrlActive = false; altActive = false
                                        lastKey = "Space"
                                    }
                                    else -> {
                                        val parts = mutableListOf<String>()
                                        if (ctrlActive) parts.add("ctrl")
                                        if (altActive) parts.add("alt")
                                        if (shiftActive && keyDef.key.length == 1) parts.add("shift")
                                        parts.add(keyDef.key)

                                        if (parts.size > 1) {
                                            onComboPress(parts.joinToString("+"))
                                            lastKey = parts.joinToString("+")
                                        } else {
                                            val k = if (shiftActive && keyDef.key.length == 1)
                                                keyDef.key.uppercase() else keyDef.key
                                            onKeyPress(k)
                                            lastKey = keyDef.label
                                        }

                                        if (ctrlActive || altActive) {
                                            ctrlActive = false; altActive = false
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
    }
}

@Composable
private fun ModifierPill(label: String, color: Color) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(color.copy(alpha = 0.2f))
            .border(1.dp, color.copy(alpha = 0.6f), RoundedCornerShape(4.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(label, color = color, fontSize = 10.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
fun KeyboardKey(
    keyDef: KeyDef,
    isModifierActive: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    var pressed by remember { mutableStateOf(false) }

    val bg by animateColorAsState(
        targetValue = when {
            pressed -> Color(0xFF6B4FC8)
            isModifierActive -> KeyBgActive
            MODIFIER_KEYS.contains(keyDef.key) -> KeyBgModifier
            else -> KeyBg
        },
        animationSpec = tween(if (pressed) 0 else 120),
        label = "keyBg"
    )
    val border by animateColorAsState(
        targetValue = if (isModifierActive || pressed) KeyBorderActive else KeyBorder,
        animationSpec = tween(100),
        label = "keyBorder"
    )
    val textColor = when {
        isModifierActive || pressed -> Color.White
        MODIFIER_KEYS.contains(keyDef.key) -> Color(0xFFCCCEFF)
        else -> Color(0xFFAAACC8)
    }

    Box(
        modifier = modifier
            .height(42.dp)
            .padding(1.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(bg)
            .border(1.dp, border, RoundedCornerShape(6.dp))
            .clickable {
                pressed = true
                onClick()
                // Reset press state after brief flash
                pressed = false
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = keyDef.label,
            color = textColor,
            fontSize = if (keyDef.label.length > 3) 8.sp else 11.sp,
            fontWeight = if (isModifierActive) FontWeight.Bold else FontWeight.Normal,
            textAlign = TextAlign.Center,
            maxLines = 1,
        )
    }
}
