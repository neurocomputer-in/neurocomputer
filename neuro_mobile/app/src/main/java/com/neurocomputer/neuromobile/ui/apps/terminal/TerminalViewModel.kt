package com.neurocomputer.neuromobile.ui.apps.terminal

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.service.TerminalWsService
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.File

data class TerminalUiState(
    val keyboardOn: Boolean = false,
    val isRecording: Boolean = false,
    val isTranscribing: Boolean = false,
)

@HiltViewModel(assistedFactory = TerminalViewModel.Factory::class)
class TerminalViewModel @AssistedInject constructor(
    @Assisted val cid: String,
    val terminalWs: TerminalWsService,
    private val httpClient: OkHttpClient,
    private val backendUrlRepository: BackendUrlRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    @AssistedFactory
    interface Factory {
        fun create(cid: String): TerminalViewModel
    }

    private val _ui = MutableStateFlow(TerminalUiState())
    val ui: StateFlow<TerminalUiState> = _ui.asStateFlow()

    private var mediaRecorder: MediaRecorder? = null
    private var audioFile: File? = null

    init {
        terminalWs.start()
    }

    fun setKeyboardOn(on: Boolean) = _ui.update { it.copy(keyboardOn = on) }

    /** Record a short voice clip; on stop, upload to /transcribe and forward the
     *  text to the supplied callback (which writes it to the pty). */
    fun startVoiceCapture() {
        if (_ui.value.isRecording || _ui.value.isTranscribing) return
        try {
            val file = File(context.cacheDir, "term_voice_${System.currentTimeMillis()}.m4a")
            audioFile = file
            @Suppress("DEPRECATION")
            mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(context)
            } else {
                MediaRecorder()
            }
            mediaRecorder!!.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            _ui.update { it.copy(isRecording = true) }
        } catch (_: Exception) {
            releaseRecorder()
        }
    }

    fun stopVoiceCapture(onTranscribed: (String) -> Unit) {
        if (!_ui.value.isRecording) return
        try { mediaRecorder?.stop() } catch (_: Exception) {}
        releaseRecorder()
        val file = audioFile ?: run {
            _ui.update { it.copy(isRecording = false) }
            return
        }
        audioFile = null
        _ui.update { it.copy(isRecording = false, isTranscribing = true) }

        viewModelScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("file", "voice.m4a", file.asRequestBody("audio/m4a".toMediaType()))
                    .build()
                val responseBody = withContext(Dispatchers.IO) {
                    httpClient.newCall(
                        Request.Builder().url("$baseUrl/transcribe").post(body).build()
                    ).execute().use { it.body?.string() ?: "" }
                }
                file.delete()
                val text = JSONObject(responseBody).optString("text", "").trim()
                if (text.isNotEmpty()) onTranscribed(text)
            } catch (_: Exception) {
                file.delete()
            } finally {
                _ui.update { it.copy(isTranscribing = false) }
            }
        }
    }

    fun cancelVoiceCapture() {
        try { mediaRecorder?.stop() } catch (_: Exception) {}
        releaseRecorder()
        audioFile?.delete()
        audioFile = null
        _ui.update { it.copy(isRecording = false) }
    }

    private fun releaseRecorder() {
        try { mediaRecorder?.release() } catch (_: Exception) {}
        mediaRecorder = null
    }

    override fun onCleared() {
        super.onCleared()
        cancelVoiceCapture()
        terminalWs.close()
    }
}
