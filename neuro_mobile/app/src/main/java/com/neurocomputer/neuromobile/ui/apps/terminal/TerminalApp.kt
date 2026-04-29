package com.neurocomputer.neuromobile.ui.apps.terminal

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun TerminalApp(cid: String, modifier: Modifier = Modifier) {
    val viewModel = hiltViewModel<TerminalViewModel, TerminalViewModel.Factory>(
        key = cid,
        creationCallback = { factory -> factory.create(cid) }
    )
    val state by viewModel.state.collectAsState()

    Column(
        modifier
            .fillMaxSize()
            .background(Color(0xFF0d1117))
            .windowInsetsPadding(WindowInsets.ime)
    ) {
        TerminalOutputView(
            lines = state.lines,
            modifier = Modifier.weight(1f),
        )
        // OS IME keyboard — no custom keyboard, avoids viewport-reflow issues
        TextField(
            value = state.inputText,
            onValueChange = viewModel::onInputChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(4.dp),
            textStyle = TextStyle(
                color = Color(0xFF00ff88),
                fontFamily = FontFamily.Monospace,
                fontSize = 13.sp,
            ),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = { viewModel.sendLine() }),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = Color(0xFF1a1f27),
                unfocusedContainerColor = Color(0xFF1a1f27),
            ),
            placeholder = {
                Text(
                    "$ ",
                    color = Color(0xFF336633),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 13.sp,
                )
            },
            singleLine = true,
        )
    }
}
