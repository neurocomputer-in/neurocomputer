package com.neurocomputer.neuromobile.ui.apps.terminal

import android.Manifest
import android.content.Context
import android.graphics.Typeface
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.inputmethod.InputMethodManager
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Backspace
import androidx.compose.material.icons.automirrored.filled.KeyboardReturn
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.neurocomputer.neuromobile.data.service.TerminalEvent
import com.neurocomputer.neuromobile.data.service.TerminalWsService
import com.termux.terminal.TerminalSession
import com.termux.terminal.TerminalSessionClient
import com.termux.view.TerminalView
import com.termux.view.TerminalViewClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

private val TerminalBg = Color(0xFF0a0a0b)
private val PanelBg = Color(0xFF111118)
private val KeyBg = Color(0xFF1f2937)
private val KeyBorder = Color(0xFF2f3a4d)
private val Accent = Color(0xFF8B5CF6)

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun TerminalApp(cid: String, modifier: Modifier = Modifier) {
    val viewModel = hiltViewModel<TerminalViewModel, TerminalViewModel.Factory>(
        key = cid,
        creationCallback = { factory -> factory.create(cid) },
    )
    val ws = viewModel.terminalWs
    val ui by viewModel.ui.collectAsState()
    val ctx = LocalContext.current

    val bridge = remember(cid) { TerminalBridge(ws) }
    var terminalView by remember { mutableStateOf<TerminalView?>(null) }

    DisposableEffect(bridge) { onDispose { bridge.dispose() } }

    val micPermission = rememberPermissionState(Manifest.permission.RECORD_AUDIO)

    Column(
        modifier
            .fillMaxSize()
            .background(TerminalBg)
            .windowInsetsPadding(WindowInsets.ime)
            .windowInsetsPadding(WindowInsets.navigationBars)
    ) {
        // Terminal pane — horizontal padding keeps text off the rounded screen
        // edges. TerminalView measures the inner width and computes cols off
        // its own getWidth(), so padding reduces cols cleanly.
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 6.dp, vertical = 4.dp),
        ) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { c ->
                    TerminalView(c, null).also { v ->
                        v.setBackgroundColor(TerminalBg.toArgb())
                        v.setTextSize(28)
                        v.setTypeface(Typeface.MONOSPACE)
                        v.setTerminalViewClient(NoOpTerminalViewClient)
                        // Without these the view won't accept touch focus, so
                        // requestFocus() no-ops and showSoftInput() finds no
                        // editable target → keyboard never shows.
                        v.isFocusable = true
                        v.isFocusableInTouchMode = true
                        bridge.attach(v)
                        terminalView = v
                    }
                },
            )
        }

        HotkeyRow(onSend = bridge::sendBytes)

        BottomBar(
            keyboardOn = ui.keyboardOn,
            isRecording = ui.isRecording,
            isTranscribing = ui.isTranscribing,
            onToggleKeyboard = {
                val next = !ui.keyboardOn
                viewModel.setKeyboardOn(next)
                terminalView?.let { v -> toggleIme(ctx, v, next) }
            },
            onMicPress = {
                if (micPermission.status.isGranted) viewModel.startVoiceCapture()
                else micPermission.launchPermissionRequest()
            },
            onMicRelease = {
                viewModel.stopVoiceCapture { text ->
                    // Push the transcript + Enter so the command executes.
                    bridge.sendText("$text\n")
                }
            },
            onMicCancel = viewModel::cancelVoiceCapture,
            onEnter = { bridge.sendBytes(byteArrayOf(0x0d)) },
            onBackspace = { bridge.sendBytes(byteArrayOf(0x7f)) },
        )
    }
}

private fun toggleIme(ctx: Context, view: TerminalView, show: Boolean) {
    val imm = ctx.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
    if (show) {
        view.requestFocus()
        imm.showSoftInput(view, InputMethodManager.SHOW_IMPLICIT)
    } else {
        imm.hideSoftInputFromWindow(view.windowToken, 0)
    }
}

// ── Hotkey row ──────────────────────────────────────────────────────────────

private data class HotKey(val label: String, val bytes: ByteArray)

private val HOTKEYS = listOf(
    HotKey("ESC", byteArrayOf(0x1b)),
    HotKey("TAB", byteArrayOf(0x09)),
    HotKey("↑",  byteArrayOf(0x1b, '['.code.toByte(), 'A'.code.toByte())),
    HotKey("↓",  byteArrayOf(0x1b, '['.code.toByte(), 'B'.code.toByte())),
    HotKey("←",  byteArrayOf(0x1b, '['.code.toByte(), 'D'.code.toByte())),
    HotKey("→",  byteArrayOf(0x1b, '['.code.toByte(), 'C'.code.toByte())),
    HotKey("^C", byteArrayOf(0x03)),
    HotKey("^D", byteArrayOf(0x04)),
    HotKey("^L", byteArrayOf(0x0c)),
    HotKey("^Z", byteArrayOf(0x1a)),
    HotKey("/",  byteArrayOf('/'.code.toByte())),
    HotKey("|",  byteArrayOf('|'.code.toByte())),
    HotKey("-",  byteArrayOf('-'.code.toByte())),
    HotKey("~",  byteArrayOf('~'.code.toByte())),
)

@Composable
private fun HotkeyRow(onSend: (ByteArray) -> Unit) {
    val scroll = rememberScrollState()
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(PanelBg)
            .horizontalScroll(scroll)
            .padding(horizontal = 6.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        HOTKEYS.forEach { key ->
            HotkeyButton(label = key.label, onClick = { onSend(key.bytes) })
        }
    }
}

@Composable
private fun HotkeyButton(label: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .heightIn(min = 32.dp)
            .background(KeyBg, RoundedCornerShape(6.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = label,
            color = Color(0xFFcfd6e3),
            fontFamily = FontFamily.Monospace,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

// ── Bottom bar (mic + keyboard toggle) ─────────────────────────────────────

@Composable
private fun BottomBar(
    keyboardOn: Boolean,
    isRecording: Boolean,
    isTranscribing: Boolean,
    onToggleKeyboard: () -> Unit,
    onMicPress: () -> Unit,
    onMicRelease: () -> Unit,
    onMicCancel: () -> Unit,
    onEnter: () -> Unit,
    onBackspace: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(PanelBg)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        IconButton(
            onClick = onToggleKeyboard,
            modifier = Modifier
                .size(40.dp)
                .background(if (keyboardOn) Accent.copy(alpha = 0.25f) else KeyBg, RoundedCornerShape(8.dp)),
        ) {
            Icon(
                Icons.Default.Keyboard,
                contentDescription = if (keyboardOn) "Hide keyboard" else "Show keyboard",
                tint = if (keyboardOn) Accent else Color(0xFFcfd6e3),
                modifier = Modifier.size(20.dp),
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        if (isTranscribing) {
            CircularProgressIndicator(
                modifier = Modifier.size(20.dp),
                color = Accent,
                strokeWidth = 2.dp,
            )
            Text("Transcribing…", color = Color(0xFF8888aa), fontSize = 12.sp)
        }

        // Backspace — sends DEL (0x7f), the byte modern xterm-class shells
        // bind to readline's backward-delete-char.
        IconButton(
            onClick = onBackspace,
            modifier = Modifier
                .size(40.dp)
                .background(KeyBg, RoundedCornerShape(8.dp)),
        ) {
            Icon(
                Icons.AutoMirrored.Filled.Backspace,
                contentDescription = "Backspace",
                tint = Color(0xFFcfd6e3),
                modifier = Modifier.size(20.dp),
            )
        }

        // Enter — sends CR (0x0d). PTY cooked mode translates to newline and
        // submits the line.
        IconButton(
            onClick = onEnter,
            modifier = Modifier
                .size(40.dp)
                .background(KeyBg, RoundedCornerShape(8.dp)),
        ) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardReturn,
                contentDescription = "Enter",
                tint = Color(0xFFcfd6e3),
                modifier = Modifier.size(20.dp),
            )
        }

        // Tap-to-toggle mic. Hold-to-talk would be nicer but tap matches the
        // chat input pattern and avoids long-press conflicts with text-select.
        IconButton(
            onClick = if (isRecording) onMicRelease else onMicPress,
            modifier = Modifier
                .size(40.dp)
                .background(
                    if (isRecording) Color(0xFF7a1a1a) else KeyBg,
                    RoundedCornerShape(8.dp),
                ),
        ) {
            Icon(
                if (isRecording) Icons.Default.Stop else Icons.Default.Mic,
                contentDescription = if (isRecording) "Stop & send" else "Voice input",
                tint = if (isRecording) Color(0xFFff8888) else Color(0xFFcfd6e3),
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

// ── Bridge: wires the WS service to a TerminalSession + TerminalView ────────

private class TerminalBridge(private val ws: TerminalWsService) {
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var pumpJob: Job? = null
    private var session: TerminalSession? = null

    fun attach(view: TerminalView) {
        val client = ViewBackedSessionClient(view)
        val s = object : TerminalSession(
            object : TerminalSession.RemoteOutputHandler {
                override fun onTerminalOutput(data: ByteArray, offset: Int, count: Int) {
                    ws.sendBytes(data, offset, count)
                }
            },
            /* transcriptRows = */ 4000,
            client,
        ) {
            override fun onRemoteResize(columns: Int, rows: Int) {
                ws.resize(columns, rows)
            }
        }
        session = s
        view.attachSession(s)

        pumpJob = scope.launch {
            ws.events.collect { ev ->
                if (ev is TerminalEvent.Bytes) {
                    s.appendRemoteOutput(ev.data, ev.data.size)
                }
            }
        }
    }

    fun sendBytes(bytes: ByteArray) {
        session?.write(bytes, 0, bytes.size)
    }

    fun sendText(text: String) = sendBytes(text.toByteArray(Charsets.UTF_8))

    fun dispose() {
        pumpJob?.cancel()
        scope.cancel()
        session?.finishIfRunning()
        session = null
    }
}

private class ViewBackedSessionClient(private val view: TerminalView) : TerminalSessionClient {
    override fun onTextChanged(s: TerminalSession) { view.onScreenUpdated() }
    override fun onTitleChanged(s: TerminalSession) = Unit
    override fun onSessionFinished(s: TerminalSession) = Unit
    override fun onCopyTextToClipboard(s: TerminalSession, text: String) = Unit
    override fun onPasteTextFromClipboard(s: TerminalSession?) = Unit
    override fun onBell(s: TerminalSession) = Unit
    override fun onColorsChanged(s: TerminalSession) = Unit
    override fun onTerminalCursorStateChange(state: Boolean) = Unit
    override fun setTerminalShellPid(s: TerminalSession, pid: Int) = Unit
    override fun getTerminalCursorStyle(): Int? = null
    override fun logError(tag: String, message: String) = Unit
    override fun logWarn(tag: String, message: String) = Unit
    override fun logInfo(tag: String, message: String) = Unit
    override fun logDebug(tag: String, message: String) = Unit
    override fun logVerbose(tag: String, message: String) = Unit
    override fun logStackTraceWithMessage(tag: String, message: String, e: Exception) = Unit
    override fun logStackTrace(tag: String, e: Exception) = Unit
}

private object NoOpTerminalViewClient : TerminalViewClient {
    override fun onScale(scale: Float): Float = 1f
    override fun onSingleTapUp(e: MotionEvent) = Unit
    override fun shouldBackButtonBeMappedToEscape(): Boolean = false
    override fun shouldEnforceCharBasedInput(): Boolean = false
    override fun shouldUseCtrlSpaceWorkaround(): Boolean = false
    override fun isTerminalViewSelected(): Boolean = true
    override fun copyModeChanged(copyMode: Boolean) = Unit
    override fun onKeyDown(keyCode: Int, e: KeyEvent, session: TerminalSession): Boolean = false
    override fun onKeyUp(keyCode: Int, e: KeyEvent): Boolean = false
    override fun onLongPress(event: MotionEvent): Boolean = false
    override fun readControlKey(): Boolean = false
    override fun readAltKey(): Boolean = false
    override fun readShiftKey(): Boolean = false
    override fun readFnKey(): Boolean = false
    override fun onCodePoint(codePoint: Int, ctrlDown: Boolean, session: TerminalSession): Boolean = false
    override fun onEmulatorSet() = Unit
    override fun logError(tag: String, message: String) = Unit
    override fun logWarn(tag: String, message: String) = Unit
    override fun logInfo(tag: String, message: String) = Unit
    override fun logDebug(tag: String, message: String) = Unit
    override fun logVerbose(tag: String, message: String) = Unit
    override fun logStackTraceWithMessage(tag: String, message: String, e: Exception) = Unit
    override fun logStackTrace(tag: String, e: Exception) = Unit
}
