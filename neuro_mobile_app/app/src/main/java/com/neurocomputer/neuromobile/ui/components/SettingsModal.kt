package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository
) : ViewModel() {

    private val _backendUrl = MutableStateFlow("")
    val backendUrl: StateFlow<String> = _backendUrl.asStateFlow()

    private val _isSaving = MutableStateFlow(false)
    val isSaving: StateFlow<Boolean> = _isSaving.asStateFlow()

    val rotateDesktop: StateFlow<Boolean> = backendUrlRepository.rotateDesktop

    private val _normaliseBusy = MutableStateFlow(false)
    val normaliseBusy: StateFlow<Boolean> = _normaliseBusy.asStateFlow()

    init {
        viewModelScope.launch {
            backendUrlRepository.currentUrl.collect { url ->
                _backendUrl.value = url
            }
        }
    }

    fun updateUrl(url: String) {
        _backendUrl.value = url
    }

    fun saveUrl() {
        viewModelScope.launch {
            _isSaving.value = true
            backendUrlRepository.setUrl(_backendUrl.value)
            _isSaving.value = false
        }
    }

    fun setRotateDesktop(value: Boolean) {
        viewModelScope.launch {
            backendUrlRepository.setRotateDesktop(value)
        }
    }

    fun normaliseDesktop() {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            _normaliseBusy.value = true
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/display/normalise")
                    .post(okhttp3.RequestBody.create(null, ByteArray(0)))
                    .header("ngrok-skip-browser-warning", "true")
                    .build()
                okhttp3.OkHttpClient().newCall(request).execute().close()
            } catch (_: Exception) {
                // swallow — user can retry
            } finally {
                _normaliseBusy.value = false
            }
        }
    }
}

@Composable
fun SettingsModal(
    onDismiss: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val backendUrl by viewModel.backendUrl.collectAsState()
    val isSaving by viewModel.isSaving.collectAsState()
    val rotateDesktop by viewModel.rotateDesktop.collectAsState()
    val normaliseBusy by viewModel.normaliseBusy.collectAsState()
    val focusManager = LocalFocusManager.current

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NeuroColors.OverlayDark.copy(alpha = 0.7f))
            .clickable { onDismiss() },
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .clip(RoundedCornerShape(16.dp))
                .background(NeuroColors.BackgroundMid)
                .clickable(enabled = false) { }
        ) {
            Column(modifier = Modifier.padding(24.dp)) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Settings",
                        color = NeuroColors.TextPrimary,
                        fontSize = 24.sp
                    )

                    IconButton(onClick = onDismiss) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Close",
                            tint = NeuroColors.TextMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Backend URL Section
                Text(
                    text = "Backend URL",
                    color = NeuroColors.TextSecondary,
                    fontSize = 14.sp
                )

                Spacer(modifier = Modifier.height(8.dp))

                BasicTextField(
                    value = backendUrl,
                    onValueChange = { viewModel.updateUrl(it) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(NeuroColors.GlassPrimary)
                        .padding(12.dp),
                    textStyle = LocalTextStyle.current.copy(
                        color = NeuroColors.TextPrimary,
                        fontSize = 14.sp
                    ),
                    cursorBrush = SolidColor(NeuroColors.TextPrimary),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Uri,
                        imeAction = ImeAction.Done
                    ),
                    keyboardActions = KeyboardActions(
                        onDone = {
                            focusManager.clearFocus()
                            viewModel.saveUrl()
                        }
                    ),
                    singleLine = true,
                    decorationBox = { innerTextField ->
                        Box {
                            if (backendUrl.isEmpty()) {
                                Text(
                                    text = "https://xxxx-xxx-xxx.ngrok-free.app",
                                    color = NeuroColors.TextDim,
                                    fontSize = 14.sp
                                )
                            }
                            innerTextField()
                        }
                    }
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Tip: Change the ngrok prefix to match your tunnel",
                    color = NeuroColors.TextDim,
                    fontSize = 12.sp
                )

                Spacer(modifier = Modifier.height(20.dp))

                // Tablet-mode toggle
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Rotate desktop display",
                            color = NeuroColors.TextPrimary,
                            fontSize = 14.sp,
                        )
                        Text(
                            text = "Flip the PC to portrait/landscape with the phone",
                            color = NeuroColors.TextDim,
                            fontSize = 12.sp,
                        )
                    }
                    Switch(
                        checked = rotateDesktop,
                        onCheckedChange = { viewModel.setRotateDesktop(it) },
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Normalise button — resets xrandr on all outputs to "normal"
                OutlinedButton(
                    onClick = { viewModel.normaliseDesktop() },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !normaliseBusy,
                    shape = RoundedCornerShape(8.dp),
                ) {
                    if (normaliseBusy) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            color = NeuroColors.TextPrimary,
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text("Normalise desktop displays", fontSize = 14.sp)
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Save Button
                Button(
                    onClick = {
                        viewModel.saveUrl()
                        onDismiss()
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isSaving,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = NeuroColors.Primary,
                        contentColor = NeuroColors.BackgroundDark
                    ),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = NeuroColors.BackgroundDark,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text("Save", fontSize = 16.sp)
                    }
                }
            }
        }
    }
}
