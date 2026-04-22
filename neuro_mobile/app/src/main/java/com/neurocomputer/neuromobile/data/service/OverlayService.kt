package com.neurocomputer.neuromobile.data.service

import android.app.Activity
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.TextButton
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.foundation.Image
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.RenderEffect
import androidx.compose.ui.graphics.asComposeRenderEffect
import androidx.compose.ui.graphics.graphicsLayer
import androidx.core.app.NotificationCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.lifecycle.setViewTreeViewModelStoreOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.neurocomputer.neuromobile.MainActivity
import com.neurocomputer.neuromobile.NeuroMobileApp
import com.neurocomputer.neuromobile.ui.activities.CaptureActivity
import com.neurocomputer.neuromobile.R
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.graphics.Bitmap
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.FormBody
import java.io.File
import javax.inject.Inject
import kotlin.math.roundToInt

data class ChatTab(
    val cid: String,
    val title: String
)

@AndroidEntryPoint
class OverlayService : Service(), LifecycleOwner, ViewModelStoreOwner, androidx.savedstate.SavedStateRegistryOwner {

    @Inject
    lateinit var backendUrlRepository: BackendUrlRepository

    @Inject
    lateinit var webSocketService: WebSocketService

    @Inject
    lateinit var chatDataChannelService: ChatDataChannelService

    private lateinit var windowManager: WindowManager
    private var composeView: ComposeView? = null
    private lateinit var params: WindowManager.LayoutParams
    
    private val lifecycleRegistry = LifecycleRegistry(this)
    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val viewModelStore = ViewModelStore()
    
    private val savedStateRegistryController = androidx.savedstate.SavedStateRegistryController.create(this)
    override val savedStateRegistry = savedStateRegistryController.savedStateRegistry

    private val scope = CoroutineScope(Dispatchers.Main + Job())

    private var mediaRecorder: MediaRecorder? = null
    private var voiceFile: File? = null
    private var isRecording = mutableStateOf(false)
    private var isMuted = mutableStateOf(false)
    private var isCapturing = false
    private var currentCid = mutableStateOf("mobile_overlay")
    private var selectedAgentType = mutableStateOf("neuro")
    private var showJobsSheet = mutableStateOf(false)
    private var jobsList = mutableStateOf<List<Map<String, Any>>>(emptyList())
    // Chat panel state
    private var showChatPanel = mutableStateOf(false)
    private var chatMessages = mutableStateOf<List<Map<String, Any>>>(emptyList())
    private var chatInputText = mutableStateOf("")
    private var chatLoading = mutableStateOf(false)
    // Tab/conversation state per agent
    private var openTabsByAgent = mutableStateOf<Map<String, List<ChatTab>>>(emptyMap())
    private var activeCidByAgent = mutableStateOf<Map<String, String?>>(emptyMap())
    // History drawer state
    private var showChatHistory = mutableStateOf(false)
    private var chatHistoryList = mutableStateOf<List<ChatTab>>(emptyList())
    // Window position for absolute chat panel positioning
    private var windowX = mutableStateOf(0)
    private var windowY = mutableStateOf(0)
    private var ttsMediaPlayer: android.media.MediaPlayer? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Instance-level references (local to this service instance)
    private var localMediaProjection: MediaProjection? = null
    private lateinit var projectionManager: MediaProjectionManager
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var isCaptureRequested = false
    private var handlerThread: HandlerThread? = null
    private var backgroundHandler: Handler? = null
    private var localVirtualDisplayCreated = false

    // Upwork capture state
    private var isUpworkCapturing = mutableStateOf(false)
    private var currentJobSlug = mutableStateOf<String?>(null)

    // Chat polling state for receiving responses
    private var chatPollingJob: Job? = null
    private var chatLastMessageCount: Int = 0
    private val chatPollingIntervalMs = 1000L // 1 second
    private val chatPollingMaxAttempts = 15
    
    // Flag to track if we're using LiveKit DataChannel for responses
    // When voice message is sent via LiveKit, we set this to avoid duplicate responses
    private var useLiveKitDataChannel = mutableStateOf(false)

    // Companion object: singleton state that persists across service restarts
    companion object {
        var instance: OverlayService? = null
            private set

        // Projection data needed to recreate MediaProjection after process death
        var pendingResultCode: Int = Activity.RESULT_CANCELED
        var pendingResultData: Intent? = null
        var isProjectionGranted: Boolean = false
        var globalVirtualDisplayCreated: Boolean = false

        const val ACTION_START = "com.neurocomputer.neuromobile.START_OVERLAY"
        const val ACTION_STOP = "com.neurocomputer.neuromobile.STOP_OVERLAY"
        const val ACTION_RECV_PROJECTION_DATA = "com.neurocomputer.neuromobile.RECV_PROJECTION_DATA"
        private const val NOTIFICATION_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, OverlayService::class.java).apply { action = ACTION_START }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, OverlayService::class.java).apply { action = ACTION_STOP }
            context.startService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)

        projectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager

        handlerThread = HandlerThread("OCRBackground").apply { start() }
        backgroundHandler = Handler(handlerThread!!.looper)

        // Collect WebSocket messages, add to chat and speak AI replies
        // Skip if we're using LiveKit DataChannel (to avoid duplicate responses)
        serviceScope.launch {
            webSocketService.messages.collect { msg ->
                if (useLiveKitDataChannel.value) {
                    // Skip WebSocket messages when using LiveKit DataChannel
                    return@collect
                }
                if (msg is WsMessage.Json) {
                    when (msg.topic) {
                        "assistant" -> {
                            val text = msg.data
                            if (text.isNotEmpty()) {
                                // Add to chat display
                                chatMessages.value = chatMessages.value + mapOf(
                                    "id" to "ws_${System.currentTimeMillis()}",
                                    "text" to text,
                                    "isUser" to false
                                )
                                chatLoading.value = false
                                Log.d("OverlayWS", "assistant msg: origin=[${msg.origin}], isMuted=${isMuted.value}")
                                // Overlay speaks ONLY when origin == "overlay" (overlay sent this message)
                                // Overlay does NOT speak for origin="app" or origin=null
                                if (msg.origin == "overlay" && !isMuted.value) {
                                    Log.d("OverlayWS", "Speaking AI reply via backend TTS, isLiveKitActive=${useLiveKitDataChannel.value}")
                                    speakViaBackendTts(text)
                                } else {
                                    Log.d("OverlayWS", "Not speaking: origin=${msg.origin}, isMuted=${isMuted.value}")
                                }
                            }
                        }
                        "task.done", "node.done" -> chatLoading.value = false
                        else -> {}
                    }
                }
            }
        }

        // Collect LiveKit DataChannel messages (for voice message responses)
        serviceScope.launch {
            chatDataChannelService.messages.collect { msg ->
                when (msg) {
                    is ChatMessage.TextMessage -> {
                        if (msg.sender == "agent" && msg.text.isNotEmpty()) {
                            Log.d("OverlayDC", "Received agent text message via DataChannel: ${msg.text.take(50)}")
                            chatMessages.value = chatMessages.value + mapOf(
                                "id" to msg.messageId,
                                "text" to msg.text,
                                "isUser" to false
                            )
                            chatLoading.value = false
                            // Speak if not muted and we originated the request
                            if (!isMuted.value && msg.origin == "overlay") {
                                Log.d("OverlayDC", "Speaking AI reply via backend TTS")
                                speakViaBackendTts(msg.text)
                            }
                            // Reset LiveKit flag after response received
                            delay(500)
                            useLiveKitDataChannel.value = false
                        }
                    }
                    is ChatMessage.VoiceMessage -> {
                        Log.d("OverlayDC", "Received voice message via DataChannel: ${msg.messageId}")
                        chatMessages.value = chatMessages.value + mapOf(
                            "id" to msg.messageId,
                            "text" to "",
                            "isUser" to false,
                            "audioUrl" to msg.audioUrl,
                            "isVoice" to true
                        )
                        chatLoading.value = false
                        // Reset LiveKit flag after response received
                        delay(500)
                        useLiveKitDataChannel.value = false
                    }
                    is ChatMessage.SystemMessage -> {
                        Log.d("OverlayDC", "Received system message via DataChannel: ${msg.topic}")
                        if (msg.topic == "task.done" || msg.topic == "node.done") {
                            chatLoading.value = false
                        }
                    }
                    else -> {}
                }
            }
        }

        // If we already have projection data from before (service was restarted), restore it
        if (isProjectionGranted && pendingResultCode == Activity.RESULT_OK && pendingResultData != null && !globalVirtualDisplayCreated) {
            Log.d("OverlayService", "Restoring projection from saved state")
            setupMediaProjection(pendingResultCode, pendingResultData!!)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startOverlay()
            ACTION_STOP -> stopOverlay()
            ACTION_RECV_PROJECTION_DATA -> {
                val resultCode = intent.getIntExtra("RESULT_CODE", Activity.RESULT_CANCELED)
                val resultData = intent.getParcelableExtra<Intent>("RESULT_DATA")
                if (resultCode == Activity.RESULT_OK && resultData != null) {
                    Log.d("OverlayService", "Received projection data, initializing...")
                    // Save to companion object so it survives service restarts
                    pendingResultCode = resultCode
                    pendingResultData = resultData
                    isProjectionGranted = true
                    setupMediaProjection(resultCode, resultData)
                }
            }
        }
        return START_STICKY
    }

    private fun setupMediaProjection(resultCode: Int, data: Intent) {
        // If we already have a valid projection, don't recreate it
        if (globalVirtualDisplayCreated && localMediaProjection != null) {
            Log.d("OverlayService", "Projection already active, skipping setup")
            return
        }

        // 1. Promote to Foreground Service with MediaProjection type FIRST
        updateForegroundService(true)

        // 2. NOW initialize MediaProjection
        try {
            val projection = projectionManager.getMediaProjection(resultCode, data)
            startContinuousCapture(projection)
            // Trigger first OCR
            handleOcr()
        } catch (e: Exception) {
            Log.e("OverlayService", "Failed to get MediaProjection in Service", e)
        }
    }

    private fun startOverlay() {
        if (composeView != null) return

        updateForegroundService()

        val displayMetrics = resources.displayMetrics
        val screenWidth = displayMetrics.widthPixels
        val screenHeight = displayMetrics.heightPixels

        params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 200
            y = 300
        }

        composeView = ComposeView(this).apply {
            // Set owners for Compose to work in Service
            setViewTreeLifecycleOwner(this@OverlayService)
            setViewTreeViewModelStoreOwner(this@OverlayService)
            setViewTreeSavedStateRegistryOwner(this@OverlayService)

            setContent {
                // Collect selected agent from repository for bi-directional sync
                val repoSelectedAgent by backendUrlRepository.selectedAgent.collectAsState()
                val isDragging = remember { mutableStateOf(false) }
                val isDraggingFromRight = remember { mutableStateOf(false) }
                var targetSnapX by remember { mutableStateOf<Int?>(null) }

                LaunchedEffect(targetSnapX) {
                    targetSnapX?.let { target ->
                        val anim = Animatable(params.x.toFloat())
                        anim.animateTo(target.toFloat(), spring(stiffness = Spring.StiffnessLow)) {
                            params.x = value.toInt()
                            windowX.value = params.x
                            try {
                                windowManager.updateViewLayout(composeView, params)
                            } catch (e: Exception) { }
                        }
                        targetSnapX = null
                    }
                }
                
                OverlayContent(
                    selectedAgent = repoSelectedAgent,
                    isDragging = isDragging.value,
                    isDraggingFromRight = isDraggingFromRight.value,
                    onDragStart = {
                        isDragging.value = true
                        val density = resources.displayMetrics.density
                        val windowWidthPx = (260 * density).toInt()
                        isDraggingFromRight.value = (params.x + windowWidthPx / 2 > screenWidth / 2)
                    },
                    onSelectedAgentChange = { agent ->
                        selectedAgentType.value = agent
                        // Sync to repository
                        serviceScope.launch {
                            backendUrlRepository.setSelectedAgent(agent)
                        }
                        switchAgent(agent)
                    },
                    onDrag = { dx, dy ->
                        params.x += dx.toInt()
                        params.y += dy.toInt()
                        windowX.value = params.x
                        windowY.value = params.y
                        windowManager.updateViewLayout(this, params)
                    },
                    onDragEnd = {
                        isDragging.value = false
                        val density = resources.displayMetrics.density
                        val windowWidthPx = (260 * density).toInt()
                        targetSnapX = if (params.x + windowWidthPx / 2 < screenWidth / 2) 0 else screenWidth - windowWidthPx
                    },
                    onMicClick = { toggleRecording() },
                    isRecording = isRecording.value,
                    isMuted = isMuted.value,
                    onMuteClick = { isMuted.value = !isMuted.value },
                    onOcrClick = { handleOcr() },
                    onClose = { stopOverlay() },
                    onAgentSwitch = { agentType -> switchAgent(agentType) },
                    onJobsClick = { fetchJobs() },
                    onUpworkStartCapture = { startUpworkCapture() },
                    onUpworkEndCapture = { endUpworkCapture() },
                    jobsList = jobsList.value,
                    showJobsSheet = showJobsSheet.value,
                    onDismissJobsSheet = { showJobsSheet.value = false },
                    showChatPanel = showChatPanel.value,
                    chatMessages = chatMessages.value,
                    chatInputText = chatInputText.value,
                    onChatToggle = { toggleChatPanel() },
                    onChatInputChange = { updateChatInput(it) },
                    onChatSend = { sendChatMessage() },
                    chatTabs = openTabsByAgent.value[selectedAgentType.value] ?: emptyList(),
                    activeTabCid = activeCidByAgent.value[selectedAgentType.value],
                    onTabSelect = { selectChatTab(it) },
                    onTabClose = { closeChatTab(it) },
                    onNewTab = { createNewChatTab() },
                    showChatHistory = showChatHistory.value,
                    chatHistoryList = chatHistoryList.value,
                    onShowHistory = { loadChatHistory() },
                    onDismissHistory = { showChatHistory.value = false },
                    onOpenChatFromHistory = { cid, title -> openChatFromHistory(cid, title) },
                    screenWidth = screenWidth,
                    screenHeight = screenHeight,
                    windowX = windowX.value,
                    windowY = windowY.value
                )
            }
        }

        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
        windowManager.addView(composeView, params)
    }

    fun updateForegroundService(capturing: Boolean = false) {
        this.isCapturing = capturing
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            var type = android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE or 
                       android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            if (isCapturing) {
                type = type or android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            }
            startForeground(NOTIFICATION_ID, createNotification(), type)
        } else {
            startForeground(NOTIFICATION_ID, createNotification())
        }
    }

    private fun stopOverlay() {
        if (isRecording.value) {
            stopRecording(false)
        }
        localMediaProjection?.stop()
        localMediaProjection = null
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
        globalVirtualDisplayCreated = false
        isProjectionGranted = false
        pendingResultCode = Activity.RESULT_CANCELED
        pendingResultData = null
        handlerThread?.quitSafely()
        handlerThread = null

        composeView?.let { windowManager.removeView(it) }
        composeView = null
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun toggleRecording() {
        if (isRecording.value) {
            stopRecording(true)
        } else {
            // Ensure connected to last session before recording
            if (currentCid.value == "mobile_overlay") {
                connectToLastSession()
            }
            startRecording()
        }
    }

    private fun startRecording() {
        try {
            voiceFile = File(cacheDir, "overlay_voice_${System.currentTimeMillis()}.m4a")
            mediaRecorder = MediaRecorder().apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(voiceFile?.absolutePath)
                prepare()
                start()
            }
            isRecording.value = true
            Log.d("OverlayService", "Recording started")
        } catch (e: Exception) {
            Log.e("OverlayService", "Failed to start recording", e)
        }
    }

    private fun stopRecording(submit: Boolean) {
        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            isRecording.value = false

            if (submit) {
                uploadVoiceFile(voiceFile)
            }
            Log.d("OverlayService", "Recording stopped (submit=$submit)")
        } catch (e: Exception) {
            Log.e("OverlayService", "Failed to stop recording", e)
            isRecording.value = false
        }
    }

    private fun uploadVoiceFile(file: File?) {
        if (file == null || !file.exists()) return

        // Show placeholder while uploading
        val placeholderId = "voice_${System.currentTimeMillis()}"
        chatMessages.value = chatMessages.value + mapOf(
            "id" to placeholderId,
            "text" to "(Transcribing...)",
            "isUser" to true
        )
        chatLoading.value = true

        serviceScope.launch {
            // Mark this message as coming from overlay so only overlay speaks the response
            webSocketService.markMessageOrigin("overlay")
            
            // Wait up to 5s for a real cid (in case connectToLastSession is still running)
            var waited = 0
            while (currentCid.value == "mobile_overlay" && waited < 50) {
                delay(100)
                waited++
            }
            if (currentCid.value == "mobile_overlay") {
                Log.e("OverlayService", "No valid cid available for upload")
                chatMessages.value = chatMessages.value.map { msg ->
                    if (msg["id"] == placeholderId) mapOf("id" to placeholderId, "text" to "(No session)", "isUser" to true) else msg
                }
                chatLoading.value = false
                return@launch
            }

            val cid = currentCid.value
            
            // Use LiveKit DataChannel to avoid duplicate responses
            useLiveKitDataChannel.value = true
            
            // Connect to chat room via LiveKit DataChannel
            Log.d("OverlayService", "Connecting to LiveKit chat room for cid=$cid")
            val connected = chatDataChannelService.connect(cid)
            if (!connected) {
                Log.e("OverlayService", "Failed to connect to LiveKit chat room")
            } else {
                Log.d("OverlayService", "Connected to LiveKit chat room")
            }

            Log.d("OverlayService", "Uploading to cid=$cid")
            val baseUrl = backendUrlRepository.currentUrl.value
            val requestBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", file.name, file.readBytes().toRequestBody("audio/m4a".toMediaType()))
                .addFormDataPart("cid", cid)
                .addFormDataPart("origin", "overlay")
                .build()

            val request = Request.Builder()
                .url("$baseUrl/voice-message")
                .post(requestBody)
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                OkHttpClient().newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    Log.d("OverlayService", "Upload response: $body")

                    if (response.isSuccessful && body != null) {
                        val json = org.json.JSONObject(body)
                        val transcription = json.optString("transcription", "")
                        // Replace placeholder with transcription — LiveKit DataChannel will deliver AI reply
                        chatMessages.value = chatMessages.value.map { msg ->
                            if (msg["id"] == placeholderId) mapOf(
                                "id" to placeholderId,
                                "text" to transcription.ifEmpty { "(No transcription)" },
                                "isUser" to true
                            ) else msg
                        }
                        Log.d("OverlayService", "Transcription: $transcription — waiting for LiveKit response")
                    } else {
                        chatMessages.value = chatMessages.value.map { msg ->
                            if (msg["id"] == placeholderId) mapOf(
                                "id" to placeholderId,
                                "text" to "(Upload failed)",
                                "isUser" to true
                            ) else msg
                        }
                        chatLoading.value = false
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Upload failed", e)
                chatMessages.value = chatMessages.value.map { msg ->
                    if (msg["id"] == placeholderId) mapOf(
                        "id" to placeholderId,
                        "text" to "(Upload failed)",
                        "isUser" to true
                    ) else msg
                }
                chatLoading.value = false
            }
        }
    }

    fun handleOcr() {
        if (localMediaProjection == null) {
            Log.d("OverlayService", "Initial OCR - starting CaptureActivity")
            val intent = Intent(this, CaptureActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
            }
            startActivity(intent)
        } else {
            Log.d("OverlayService", "Requesting frame from existing projection session")
            isCaptureRequested = true
        }
    }

    private fun switchAgent(agentType: String) {
        // Track selected agent type for chat
        selectedAgentType.value = agentType
        scope.launch(Dispatchers.IO) {
            val baseUrl = backendUrlRepository.currentUrl.value
            val requestBody = FormBody.Builder()
                .build()

            val request = Request.Builder()
                .url("$baseUrl/agents/$agentType")
                .post(requestBody)
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                OkHttpClient().newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    Log.d("OverlayService", "Switch agent response: $body")

                    if (response.isSuccessful && body != null) {
                        val json = org.json.JSONObject(body)
                        val agentId = json.optString("agent_id")
                        Log.d("OverlayService", "Switched to agent: $agentId")
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Switch agent failed", e)
            }
        }
    }

    private fun fetchJobs() {
        scope.launch(Dispatchers.IO) {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/upwork/jobs")
                .get()
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                OkHttpClient().newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    Log.d("OverlayService", "Fetch jobs response: $body")

                    if (response.isSuccessful && body != null) {
                        val json = org.json.JSONObject(body)
                        val jobsArray = json.optJSONArray("jobs") ?: org.json.JSONArray()
                        val jobs = mutableListOf<Map<String, Any>>()
                        for (i in 0 until jobsArray.length()) {
                            val jobObj = jobsArray.getJSONObject(i)
                            val jobMap = mutableMapOf<String, Any>()
                            jobObj.keys().forEach { key ->
                                jobMap[key] = jobObj.get(key)
                            }
                            jobs.add(jobMap)
                        }
                        jobsList.value = jobs
                        showJobsSheet.value = true
                        Log.d("OverlayService", "Loaded ${jobs.size} jobs")
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Fetch jobs failed", e)
            }
        }
    }

    fun toggleChatPanel() {
        if (showChatPanel.value) {
            // Closing the panel - stop polling
            stopChatPolling()
            showChatPanel.value = false
            // Resize overlay back to small size at original position
            params.width = WindowManager.LayoutParams.WRAP_CONTENT
            params.height = WindowManager.LayoutParams.WRAP_CONTENT
            params.gravity = Gravity.TOP or Gravity.START
            params.x = 200
            params.y = 300
            composeView?.let { windowManager.updateViewLayout(it, params) }
        } else {
            // Connect to last session for this agent
            showChatPanel.value = true
            connectToLastSession()
            // Expand overlay to full screen for chat panel - center it
            params.width = WindowManager.LayoutParams.MATCH_PARENT
            params.height = WindowManager.LayoutParams.MATCH_PARENT
            params.gravity = Gravity.CENTER
            params.x = 0
            params.y = 0
            composeView?.let { windowManager.updateViewLayout(it, params) }
        }
    }

    fun selectChatTab(cid: String) {
        val agent = selectedAgentType.value
        val currentActiveCid = activeCidByAgent.value[agent]
        if (currentActiveCid != cid) {
            activeCidByAgent.value = activeCidByAgent.value.toMutableMap().apply {
                put(agent, cid)
            }
            currentCid.value = cid
            webSocketService.reconnectTo(cid)
            // Also connect via LiveKit DataChannel
            serviceScope.launch {
                chatDataChannelService.connect(cid)
            }
            loadChatMessages()
        }
    }

    fun closeChatTab(cid: String) {
        val agent = selectedAgentType.value
        val tabs = openTabsByAgent.value[agent] ?: return
        val updated = tabs.filter { it.cid != cid }
        
        // Update open tabs for this agent
        openTabsByAgent.value = openTabsByAgent.value.toMutableMap().apply {
            put(agent, updated)
        }
        
        // If closing active tab, switch to another or clear
        if (activeCidByAgent.value[agent] == cid) {
            if (updated.isNotEmpty()) {
                selectChatTab(updated.first().cid)
            } else {
                // Clear active tab for this agent
                activeCidByAgent.value = activeCidByAgent.value.toMutableMap().apply {
                    put(agent, null)
                }
                currentCid.value = "mobile_overlay"
                chatMessages.value = emptyList()
            }
        }
    }

    fun createNewChatTab() {
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agent = selectedAgentType.value
                val requestBody = """{"agent_id": "$agent"}"""
                    .toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$baseUrl/conversation")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val newCid = json.getString("cid")
                        val newTab = ChatTab(cid = newCid, title = "New Chat")
                        
                        // Add to open tabs for this agent
                        val currentTabs = openTabsByAgent.value.toMutableMap()
                        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()
                        agentTabs.add(newTab)
                        currentTabs[agent] = agentTabs
                        openTabsByAgent.value = currentTabs
                        
                        // Set as active tab
                        activeCidByAgent.value = activeCidByAgent.value.toMutableMap().apply {
                            put(agent, newCid)
                        }
                        currentCid.value = newCid
                        Log.d("OverlayService", "Created new chat tab: $newCid")
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Create new chat tab failed", e)
            }
        }
    }

    fun loadChatHistory() {
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agent = selectedAgentType.value
                val request = Request.Builder()
                    .url("$baseUrl/conversations?agent_id=$agent")
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONArray(body ?: "[]")
                        val conversations = mutableListOf<ChatTab>()
                        for (i in 0 until json.length()) {
                            val obj = json.getJSONObject(i)
                            conversations.add(ChatTab(
                                cid = obj.getString("id"),
                                title = obj.optString("title", "New Chat")
                            ))
                        }
                        chatHistoryList.value = conversations
                        showChatHistory.value = true
                        Log.d("OverlayService", "Loaded ${conversations.size} conversations")
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to load chat history", e)
            }
        }
    }

    fun openChatFromHistory(cid: String, title: String) {
        val agent = selectedAgentType.value
        
        // Check if tab already exists
        val existingTabs = openTabsByAgent.value[agent] ?: emptyList()
        if (existingTabs.none { it.cid == cid }) {
            // Add new tab
            val newTab = ChatTab(cid = cid, title = title)
            openTabsByAgent.value = openTabsByAgent.value.toMutableMap().apply {
                put(agent, existingTabs + newTab)
            }
        }
        
        // Set as active
        activeCidByAgent.value = activeCidByAgent.value.toMutableMap().apply {
            put(agent, cid)
        }
        currentCid.value = cid
        
        // Close history and load messages
        showChatHistory.value = false
        loadChatMessages()
    }

    private fun connectToLastSession() {
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agent = selectedAgentType.value
                // Fetch recent conversations for this agent
                val request = Request.Builder()
                    .url("$baseUrl/conversations?agent_id=$agent")
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONArray(body ?: "[]")
                        if (json.length() > 0) {
                            // Use the most recent conversation
                            val lastConv = json.getJSONObject(0)
                            val cid = lastConv.getString("id")
                            val title = lastConv.optString("title", "New Chat")
                            Log.d("OverlayService", "Connecting to last session: $cid")
                            currentCid.value = cid
                            // Add as open tab
                            val currentTabs = openTabsByAgent.value.toMutableMap()
                            val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()
                            if (agentTabs.none { it.cid == cid }) {
                                agentTabs.add(0, ChatTab(cid = cid, title = title))
                            }
                            currentTabs[agent] = agentTabs
                            openTabsByAgent.value = currentTabs
                            activeCidByAgent.value = activeCidByAgent.value.toMutableMap().apply { put(agent, cid) }
                        } else {
                            // No existing conversations — create one
                            createNewChatTab()
                        }
                    }
                }
                // Connect WebSocket to active cid
                webSocketService.reconnectTo(currentCid.value)
                Log.d("OverlayService", "WebSocket connected to ${currentCid.value}")
                // Also connect via LiveKit DataChannel
                serviceScope.launch {
                    chatDataChannelService.connect(currentCid.value)
                }
                loadChatMessages()
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to connect to last session", e)
            }
        }
    }

    private fun loadChatMessages() {
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = Request.Builder()
                    .url("$baseUrl/conversation/${currentCid.value}")
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val messagesArray = json.getJSONArray("messages")
                        val msgs = mutableListOf<Map<String, Any>>()
                        for (i in 0 until messagesArray.length()) {
                            val msgObj = messagesArray.getJSONObject(i)
                            msgs.add(mapOf(
                                "id" to msgObj.optString("id", "$i"),
                                "text" to msgObj.optString("content", ""),
                                "isUser" to (msgObj.optString("role") == "user")
                            ))
                        }
                        chatMessages.value = msgs
                        // Sync polling state with loaded messages
                        chatLastMessageCount = msgs.size
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to load chat messages", e)
            }
        }
    }

    fun sendChatMessage() {
        val text = chatInputText.value.trim()
        if (text.isEmpty()) return

        // Add user message locally
        chatMessages.value = chatMessages.value + mapOf(
            "id" to "user_${System.currentTimeMillis()}",
            "text" to text,
            "isUser" to true
        )
        chatInputText.value = ""
        chatLoading.value = true

        // Record message count before sending so we can detect new responses
        chatLastMessageCount = chatMessages.value.size

        serviceScope.launch {
            // Mark this message as coming from overlay so only overlay speaks the response
            webSocketService.markMessageOrigin("overlay")
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = """{"cid":"${currentCid.value}","text":"$text"}"""
                    .toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$baseUrl/chat")
                    .post(body)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    // Response comes via WebSocket
                    response.close()
                }
                // WS handles reply — no polling needed
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to send chat message", e)
                chatLoading.value = false
            }
        }
    }

    fun updateChatInput(text: String) {
        chatInputText.value = text
    }

    private fun startChatPolling() {
        // Cancel any existing polling
        stopChatPolling()

        var attempts = 0
        chatPollingJob = serviceScope.launch {
            while (attempts < chatPollingMaxAttempts && isUpworkCapturing.value == false) {
                delay(chatPollingIntervalMs)
                attempts++

                try {
                    val baseUrl = backendUrlRepository.currentUrl.value
                    val request = Request.Builder()
                        .url("$baseUrl/conversation/${currentCid.value}")
                        .get()
                        .header("ngrok-skip-browser-warning", "true")
                        .build()

                    OkHttpClient().newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            val body = response.body?.string()
                            val json = org.json.JSONObject(body ?: "{}")
                            val messagesArray = json.getJSONArray("messages")
                            val serverMessageCount = messagesArray.length()

                            // Check if there are new messages from the server
                            if (serverMessageCount > chatLastMessageCount) {
                                Log.d("OverlayService", "Chat polling: found ${serverMessageCount - chatLastMessageCount} new message(s)")

                                // Build the new messages list
                                val currentLocalCount = chatMessages.value.size
                                val newMessages = mutableListOf<Map<String, Any>>()

                                for (i in currentLocalCount until messagesArray.length()) {
                                    val msgObj = messagesArray.getJSONObject(i)
                                    newMessages.add(mapOf(
                                        "id" to msgObj.optString("id", "$i"),
                                        "text" to msgObj.optString("content", ""),
                                        "isUser" to (msgObj.optString("role") == "user")
                                    ))
                                }

                                // Append new messages to local state
                                if (newMessages.isNotEmpty()) {
                                    chatMessages.value = chatMessages.value + newMessages
                                    chatLastMessageCount = chatMessages.value.size
                                }

                                // Check if we have an assistant response yet
                                val hasAssistantResponse = newMessages.any { it["isUser"] == false }
                                if (hasAssistantResponse) {
                                    chatLoading.value = false
                                    stopChatPolling()
                                    return@launch
                                }
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e("OverlayService", "Chat polling error: ${e.message}")
                }
            }

            // After max attempts, stop loading indicator
            chatLoading.value = false
            Log.d("OverlayService", "Chat polling completed after $attempts attempts")
        }
    }

    private fun stopChatPolling() {
        chatPollingJob?.cancel()
        chatPollingJob = null
    }

    fun startContinuousCapture(projection: MediaProjection) {
        this.localMediaProjection = projection

        // Android 14+ requirement: MUST register callback BEFORE starting capture (createVirtualDisplay)
        projection.registerCallback(object : MediaProjection.Callback() {
            override fun onCapturedContentResize(width: Int, height: Int) {
                Log.d("OverlayService", "Screen resized to $width x $height")
                // Note: We cannot call createVirtualDisplay again on the same MediaProjection.
                // The VirtualDisplay handles content resizing automatically.
            }
            override fun onStop() {
                cleanupCapture()
            }
        }, backgroundHandler)

        setupVirtualDisplay()
    }

    private fun setupVirtualDisplay(requestedWidth: Int = 0, requestedHeight: Int = 0) {
        // Prevent multiple createVirtualDisplay calls - Android only allows ONE per MediaProjection session
        if (globalVirtualDisplayCreated) {
            Log.d("OverlayService", "VirtualDisplay already created, skipping recreation")
            return
        }

        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = android.util.DisplayMetrics()
        wm.defaultDisplay.getRealMetrics(metrics)

        val width = if (requestedWidth > 0) requestedWidth else metrics.widthPixels
        val height = if (requestedHeight > 0) requestedHeight else metrics.heightPixels
        val density = metrics.densityDpi

        if (width <= 0 || height <= 0) {
            Log.e("OverlayService", "Invalid dimensions for VirtualDisplay: ${width}x${height}")
            return
        }

        // Cleanup old resources
        virtualDisplay?.release()
        imageReader?.close()

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        imageReader?.setOnImageAvailableListener({ reader ->
            val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener

            if (isCaptureRequested) {
                isCaptureRequested = false
                Log.d("OverlayService", "Capturing frame for OCR")

                val planes = image.planes
                val buffer = planes[0].buffer
                val pixelStride = planes[0].pixelStride
                val rowStride = planes[0].rowStride
                val rowPadding = rowStride - pixelStride * width

                val bitmap = Bitmap.createBitmap(
                    width + rowPadding / pixelStride, height,
                    Bitmap.Config.ARGB_8888
                )
                bitmap.copyPixelsFromBuffer(buffer)
                val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height)

                processOcr(croppedBitmap)
            }
            image.close()
        }, backgroundHandler)

        updateForegroundService(true)
        try {
            virtualDisplay = localMediaProjection?.createVirtualDisplay(
                "NeuroContinuousOCR",
                width, height, density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader?.surface, null, backgroundHandler
            )
            globalVirtualDisplayCreated = true
        } catch (e: Exception) {
            Log.e("OverlayService", "Failed to create VirtualDisplay", e)
        }
    }

    private fun cleanupCapture() {
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
        localMediaProjection = null
        globalVirtualDisplayCreated = false
        isProjectionGranted = false
        updateForegroundService(false)
    }

    private fun processOcr(bitmap: Bitmap) {
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        val image = InputImage.fromBitmap(bitmap, 0)

        recognizer.process(image)
            .addOnSuccessListener { visionText ->
                val fullText = visionText.text
                if (fullText.isNotEmpty()) {
                    if (isUpworkCapturing.value) {
                        // In Upwork capture mode - send to upwork capture endpoint
                        submitUpworkFrame(fullText)
                    } else {
                        // Normal mode - send via LiveKit for agent processing
                        submitOcrViaLiveKit(fullText)
                    }
                }
            }
    }

    private fun speakViaBackendTts(text: String) {
        Log.d("OverlayService", "speakViaBackendTts CALLED with text: ${text.take(50)}, isLiveKitActive=${useLiveKitDataChannel.value}")
        serviceScope.launch {
            try {
                // Stop any currently playing audio
                ttsMediaPlayer?.release()
                ttsMediaPlayer = null

                val baseUrl = backendUrlRepository.currentUrl.value
                val cid = currentCid.value
                val reqBody = """{"text":"$text","cid":"$cid","voice":"alloy"}"""
                    .toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$baseUrl/tts")
                    .post(reqBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                val response = OkHttpClient().newCall(request).execute()
                if (!response.isSuccessful) {
                    Log.e("OverlayService", "TTS request failed: ${response.code}")
                    return@launch
                }
                val bodyStr = response.body?.string() ?: run {
                    Log.e("OverlayService", "TTS response body null")
                    return@launch
                }
                val json = JSONObject(bodyStr)
                val audioUrl = json.optString("audio_url", "")
                if (audioUrl.isEmpty()) {
                    Log.e("OverlayService", "TTS audio_url empty")
                    return@launch
                }

                // Download and play audio
                val audioUrlFull = if (audioUrl.startsWith("http")) audioUrl else "$baseUrl$audioUrl"
                val audioRequest = Request.Builder()
                    .url(audioUrlFull)
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                val audioResponse = OkHttpClient().newCall(audioRequest).execute()
                if (!audioResponse.isSuccessful) {
                    Log.e("OverlayService", "Audio download failed: ${audioResponse.code}")
                    return@launch
                }

                val audioFile = File(cacheDir, "overlay_tts_${System.currentTimeMillis()}.mp3")
                audioResponse.body?.byteStream()?.use { input ->
                    audioFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }

                ttsMediaPlayer = android.media.MediaPlayer().apply {
                    setDataSource(audioFile.absolutePath)
                    prepare()
                    setOnCompletionListener {
                        Log.d("OverlayService", "TTS playback completed")
                        release()
                        ttsMediaPlayer = null
                        audioFile.delete()
                    }
                    setOnErrorListener { _, what, extra ->
                        Log.e("OverlayService", "MediaPlayer error: what=$what extra=$extra")
                        release()
                        ttsMediaPlayer = null
                        audioFile.delete()
                        true
                    }
                    start()
                }
                Log.d("OverlayService", "TTS playback started")
            } catch (e: Exception) {
                Log.e("OverlayService", "speakViaBackendTts failed", e)
            }
        }
    }

    private fun submitChat(text: String) {
        scope.launch(Dispatchers.IO) {
            // Check if we should use LiveKit DataChannel
            if (useLiveKitDataChannel.value && chatDataChannelService.connectionState.value.connected) {
                // Send via LiveKit DataChannel
                Log.d("OverlayService", "Submitting chat via LiveKit: ${text.take(50)}")
                val success = chatDataChannelService.sendTextMessage(text, origin = "overlay")
                if (success) {
                    Log.d("OverlayService", "Chat submitted via LiveKit successfully")
                } else {
                    Log.e("OverlayService", "Failed to submit chat via LiveKit, falling back to HTTP")
                    submitChatViaHttp(text)
                }
            } else {
                // Fall back to HTTP
                submitChatViaHttp(text)
            }
        }
    }

    private fun submitChatViaHttp(text: String) {
        scope.launch(Dispatchers.IO) {
            webSocketService.markMessageOrigin("overlay")
            val baseUrl = backendUrlRepository.currentUrl.value
            val jsonBody = JSONObject().apply {
                put("cid", currentCid.value)
                put("text", text)
            }

            val request = Request.Builder()
                .url("$baseUrl/chat")
                .post(jsonBody.toString().toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                val client = OkHttpClient()
                val response = client.newCall(request).execute()
                Log.d("OverlayService", "OCR Chat submitted via HTTP: ${response.code}")
                response.close()
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to submit OCR chat result", e)
            }
        }
    }

    private fun submitOcrViaLiveKit(ocrText: String) {
        scope.launch {
            Log.d("OverlayService", "Submitting OCR via LiveKit: ${ocrText.take(50)}")
            
            // Wait for valid cid
            var waited = 0
            while (currentCid.value == "mobile_overlay" && waited < 50) {
                delay(100)
                waited++
            }
            if (currentCid.value == "mobile_overlay") {
                Log.e("OverlayService", "No valid cid for OCR")
                return@launch
            }
            
            val cid = currentCid.value
            
            // Connect to chat room via LiveKit if not connected
            if (!chatDataChannelService.connectionState.value.connected || 
                chatDataChannelService.connectionState.value.conversationId != cid) {
                useLiveKitDataChannel.value = true
                val connected = chatDataChannelService.connect(cid)
                if (!connected) {
                    Log.e("OverlayService", "Failed to connect to LiveKit for OCR")
                    // Fall back to HTTP
                    submitChat("[Screen OCR]: $ocrText")
                    return@launch
                }
            }
            
            // Send OCR via LiveKit
            val success = chatDataChannelService.sendOcrMessage(ocrText, origin = "overlay")
            if (success) {
                Log.d("OverlayService", "OCR submitted via LiveKit successfully")
            } else {
                Log.e("OverlayService", "Failed to submit OCR via LiveKit, falling back to HTTP")
                submitChat("[Screen OCR]: $ocrText")
            }
        }
    }

    private fun submitUpworkFrame(frameText: String, pageUrl: String = "") {
        val slug = currentJobSlug.value ?: return
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val jsonBody = JSONObject().apply {
                    put("job_slug", slug)
                    put("frame_text", frameText)
                    put("url", pageUrl)
                }

                val request = Request.Builder()
                    .url("$baseUrl/upwork/capture")
                    .post(jsonBody.toString().toRequestBody("application/json".toMediaType()))
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    Log.d("OverlayService", "Upwork frame submitted: ${response.code}")
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to submit upwork frame", e)
            }
        }
    }

    fun startUpworkCapture() {
        if (isUpworkCapturing.value) {
            Log.d("OverlayService", "Already capturing for Upwork")
            return
        }

        // Generate a job slug based on timestamp
        val slug = "job_${System.currentTimeMillis()}"
        currentJobSlug.value = slug
        isUpworkCapturing.value = true
        Log.d("OverlayService", "Starting Upwork capture with slug: $slug")

        // Start the projection/capture flow if not already active
        if (localMediaProjection == null) {
            val intent = Intent(this, CaptureActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
            }
            startActivity(intent)
        } else {
            // Request a capture from existing projection
            isCaptureRequested = true
        }
    }

    fun endUpworkCapture() {
        val slug = currentJobSlug.value
        if (slug == null || !isUpworkCapturing.value) {
            Log.d("OverlayService", "Not currently capturing for Upwork")
            return
        }

        isUpworkCapturing.value = false
        Log.d("OverlayService", "Ending Upwork capture for slug: $slug")

        // Finalize the job via API
        serviceScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = Request.Builder()
                    .url("$baseUrl/upwork/finalize/$slug")
                    .post("".toRequestBody("application/json".toMediaType()))
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                OkHttpClient().newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    Log.d("OverlayService", "Upwork finalize response: ${response.code} - $body")

                    if (response.isSuccessful) {
                        // Refresh jobs list if jobs sheet is showing
                        if (showJobsSheet.value) {
                            fetchJobs()
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("OverlayService", "Failed to finalize upwork job", e)
            }
        }

        currentJobSlug.value = null
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, NeuroMobileApp.OVERLAY_CHANNEL_ID)
            .setContentTitle("Neuro Overlay Active")
            .setContentText("Floating controls are visible over other apps")
            .setSmallIcon(R.drawable.logo)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    override fun onDestroy() {
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
        instance = null
        ttsMediaPlayer?.release()
        ttsMediaPlayer = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

}

@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
@Composable
fun OverlayContent(
    selectedAgent: String,
    onSelectedAgentChange: (String) -> Unit,
    onDragStart: () -> Unit = {},
    onDrag: (Float, Float) -> Unit,
    onDragEnd: () -> Unit,
    isDragging: Boolean = false,
    isDraggingFromRight: Boolean = false,
    onMicClick: () -> Unit,
    isRecording: Boolean,
    @Suppress("UNUSED_PARAMETER") isMuted: Boolean,
    @Suppress("UNUSED_PARAMETER") onMuteClick: () -> Unit,
    onOcrClick: () -> Unit,
    onClose: () -> Unit,
    onAgentSwitch: (String) -> Unit = {},
    onJobsClick: () -> Unit = {},
    onUpworkStartCapture: () -> Unit = {},
    onUpworkEndCapture: () -> Unit = {},
    jobsList: List<Map<String, Any>> = emptyList(),
    showJobsSheet: Boolean = false,
    onDismissJobsSheet: () -> Unit = {},
    // Chat panel parameters
    showChatPanel: Boolean = false,
    chatMessages: List<Map<String, Any>> = emptyList(),
    chatInputText: String = "",
    onChatToggle: () -> Unit = {},
    onChatInputChange: (String) -> Unit = {},
    onChatSend: () -> Unit = {},
    // Tab parameters
    chatTabs: List<ChatTab> = emptyList(),
    activeTabCid: String? = null,
    onTabSelect: (String) -> Unit = {},
    onTabClose: (String) -> Unit = {},
    onNewTab: () -> Unit = {},
    // History parameters
    showChatHistory: Boolean = false,
    chatHistoryList: List<ChatTab> = emptyList(),
    onShowHistory: () -> Unit = {},
    onDismissHistory: () -> Unit = {},
    onOpenChatFromHistory: (String, String) -> Unit = { _, _ -> },
    // Screen dimensions
    screenWidth: Int = 0,
    screenHeight: Int = 0,
    // Window position (for absolute positioning)
    windowX: Int = 0,
    windowY: Int = 0
) {
    val coroutineScope = rememberCoroutineScope()
    // showDropdown = true when long-pressing N bubble
    var showDropdown by remember { mutableStateOf(false) }
    var isToolsExpanded by remember { mutableStateOf(true) }
    var wheelRotation by remember { mutableFloatStateOf(0f) }
    // Track tools state before showing dropdown
    var toolsExpandedBeforeDropdown by remember { mutableStateOf(true) }

    // Container for the dialer
    Box(
        modifier = Modifier
            .size(if (showChatPanel) androidx.compose.ui.unit.Dp.Unspecified else 260.dp)
    ) {
        if (isToolsExpanded && !showDropdown && !showChatPanel) {
            val windowCenterPx = windowX + (130 * LocalDensity.current.density)
            val currentSnappedRight = windowCenterPx > screenWidth / 2
            val isSnappedRight = if (isDragging) isDraggingFromRight else currentSnappedRight

            // Tools distributed in a FULL circle
            val tools: List<Pair<ImageVector, () -> Unit >> = when (selectedAgent) {
                "neuro" -> listOf(
                    Icons.Default.Call to { Log.d("Overlay", "Neuro voice clicked") },
                    (if (isRecording) Icons.Default.Stop else Icons.Default.Mic) to onMicClick,
                    Icons.Default.Screenshot to onOcrClick,
                    Icons.Default.Chat to onChatToggle,
                    Icons.Default.Close to onClose,
                    Icons.Default.Settings to { Log.d("Overlay", "Settings clicked") }
                )
                "openclaw" -> listOf(
                    Icons.Default.Call to { Log.d("Overlay", "OpenClaw voice clicked") },
                    (if (isRecording) Icons.Default.Stop else Icons.Default.Mic) to onMicClick,
                    Icons.Default.Screenshot to onOcrClick,
                    Icons.Default.Chat to onChatToggle,
                    Icons.Default.Close to onClose
                )
                "opencode" -> listOf(
                    Icons.Default.Call to { Log.d("Overlay", "OpenCode voice clicked") },
                    (if (isRecording) Icons.Default.Stop else Icons.Default.Mic) to onMicClick,
                    Icons.Default.Screenshot to onOcrClick,
                    Icons.Default.Chat to onChatToggle,
                    Icons.Default.Close to onClose
                )
                "neuroupwork" -> listOf(
                    Icons.Default.PlayArrow to { Log.d("Overlay", "Upwork start clicked") },
                    Icons.Default.Stop to { Log.d("Overlay", "Upwork stop clicked") },
                    Icons.Default.List to onJobsClick,
                    Icons.Default.Chat to onChatToggle,
                    Icons.Default.Close to onClose
                )
                else -> listOf(
                    Icons.Default.Call to { Log.d("Overlay", "${selectedAgent} voice clicked") },
                    (if (isRecording) Icons.Default.Stop else Icons.Default.Mic) to onMicClick,
                    Icons.Default.Chat to onChatToggle,
                    Icons.Default.Close to onClose
                )
            }

            val radius = 65.dp
            val totalTools = tools.size
            val rotationRad = Math.toRadians(wheelRotation.toDouble())
            
            // Animation for tool expansion - high stiffness for responsive collapse during drag
            val toolsScale by animateFloatAsState(if (isToolsExpanded && !isDragging) 1f else 0f, 
                animationSpec = spring(stiffness = Spring.StiffnessMedium, dampingRatio = Spring.DampingRatioLowBouncy), label = "wheelPop")

            // Layout Container for the sharp tools & buttons
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .pointerInput(isSnappedRight) {
                        detectDragGestures(
                            onDragStart = { },
                            onDrag = { change, _ ->
                                val center = Offset(if (isSnappedRight) this.size.width.toFloat() else 0f, this.size.height / 2f)
                                val touchPos = change.position
                                val prevTouchPos = change.previousPosition
                                
                                val currentAngle = Math.toDegrees(
                                    kotlin.math.atan2(
                                        (touchPos.y - center.y).toDouble(),
                                        (touchPos.x - center.x).toDouble()
                                    )
                                ).toFloat()
                                val prevAngle = Math.toDegrees(
                                    kotlin.math.atan2(
                                        (prevTouchPos.y - center.y).toDouble(),
                                        (prevTouchPos.x - center.x).toDouble()
                                    )
                                ).toFloat()
                                
                                var delta = currentAngle - prevAngle
                                if (delta > 180f) delta -= 360f
                                if (delta < -180f) delta += 360f
                                
                                wheelRotation += delta
                                change.consume()
                            },
                            onDragEnd = onDragEnd,
                            onDragCancel = onDragEnd
                        )
                    }
            ) {
                if (isToolsExpanded) {
                    tools.forEachIndexed { index, (icon, onClick) ->
                        val baseAngle = Math.toRadians((360.0 / totalTools) * index)
                        val rotatedAngle = baseAngle + rotationRad
                        val x = (radius.value * toolsScale * kotlin.math.cos(rotatedAngle).toFloat()).dp
                        val y = (radius.value * toolsScale * kotlin.math.sin(rotatedAngle).toFloat()).dp
                        
                        // Individual tap animation
                        var isPressed by remember { mutableStateOf(false) }
                        val scale by animateFloatAsState(if (isPressed) 1.5f else 1f, label = "toolScale")

                        Box(
                            modifier = Modifier
                                .align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart)
                                .offset(x = x, y = y)
                                .graphicsLayer {
                                    scaleX = scale * toolsScale
                                    scaleY = scale * toolsScale
                                    alpha = toolsScale
                                }
                        ) {
                            CircleToolButton(
                                icon = icon, 
                                onClick = { 
                                    isPressed = true
                                    onClick()
                                    coroutineScope.launch {
                                        delay(200)
                                        isPressed = false
                                    }
                                }
                            )
                        }
                    }
                }

                // Main agent button
                Box(modifier = Modifier.align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart)) {
                    AgentCircleButton(
                        selectedAgent = selectedAgent,
                        isRecording = isRecording,
                        onDragStart = onDragStart,
                        onDrag = onDrag,
                        onDragEnd = onDragEnd,
                        onToggleExpand = { isToolsExpanded = false },
                        onShowDropdown = { toolsExpandedBeforeDropdown = isToolsExpanded; showDropdown = true },
                        isToolsExpanded = isToolsExpanded
                    )
                }
            }
        } else if (!showDropdown && !showChatPanel) {
        val windowCenterPx = windowX + (130 * LocalDensity.current.density)
        val currentSnappedRight = windowCenterPx > screenWidth / 2
        val isSnappedRight = if (isDragging) isDraggingFromRight else currentSnappedRight

        // Collapsed state
        Box(
            modifier = Modifier
                .size(100.dp, 100.dp)
                .align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart),
            contentAlignment = if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart
        ) {
            AgentCircleButton(
                selectedAgent = selectedAgent,
                isRecording = isRecording,
                onDrag = onDrag,
                onDragEnd = onDragEnd,
                onToggleExpand = { isToolsExpanded = true },
                onShowDropdown = { toolsExpandedBeforeDropdown = isToolsExpanded; showDropdown = true },
                isToolsExpanded = isToolsExpanded
            )
        }
    }

    // ============ AGENT SELECTOR (unified with dialer look) ============
    if (showDropdown) {
        val windowCenterPx = windowX + (130 * LocalDensity.current.density)
        val currentSnappedRight = windowCenterPx > screenWidth / 2
        val isSnappedRight = if (isDragging) isDraggingFromRight else currentSnappedRight

        Box(
            modifier = Modifier
                .size(260.dp)
                .align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart)
                .pointerInput(isSnappedRight) {
                    detectDragGestures { change, _ ->
                        val center = Offset(if (isSnappedRight) this.size.width.toFloat() else 0f, this.size.height / 2f)
                        val touchPos = change.position
                        val prevTouchPos = change.previousPosition
                        
                        val currentAngle = Math.toDegrees(
                            kotlin.math.atan2(
                                (touchPos.y - center.y).toDouble(),
                                (touchPos.x - center.x).toDouble()
                            )
                        ).toFloat()
                        val prevAngle = Math.toDegrees(
                            kotlin.math.atan2(
                                (prevTouchPos.y - center.y).toDouble(),
                                (prevTouchPos.x - center.x).toDouble()
                            )
                        ).toFloat()
                        
                        var delta = currentAngle - prevAngle
                        if (delta > 180f) delta -= 360f
                        if (delta < -180f) delta += 360f
                        
                        wheelRotation += delta
                        change.consume()
                    }
                }
        ) {
            // Agents arranged in circle - ONLY show non-selected agents in the circle
            val allAgents = listOf(
                "neuro" to R.drawable.logo,
                "openclaw" to R.drawable.openclaw_logo,
                "opencode" to R.drawable.opencode_logo,
                "neuroupwork" to R.drawable.upwork_logo
            )
            val agents = allAgents.filter { it.first != selectedAgent }
            val radius = 65.dp
            val totalAgents = agents.size
            val rotationRad = Math.toRadians(wheelRotation.toDouble())
            
            agents.forEachIndexed { index, (agentId, logoRes) ->
                val baseAngle = Math.toRadians((360.0 / totalAgents) * index - 90)
                val rotatedAngle = baseAngle + rotationRad
                val x = (radius.value * kotlin.math.cos(rotatedAngle)).dp
                val y = (radius.value * kotlin.math.sin(rotatedAngle)).dp
                
                Box(
                    modifier = Modifier
                        .align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart)
                        .offset(x = x, y = y)
                        .size(56.dp)
                        .background(
                            if (selectedAgent == agentId) Color(0xFF4C1D95).copy(alpha = 0.5f) else Color(0xDD1A1A1A),
                            CircleShape
                        )
                        .border(
                            if (selectedAgent == agentId) 2.dp else 0.dp,
                            if (selectedAgent == agentId) Color.White else Color.Transparent,
                            CircleShape
                        )
                        .clickable { 
                                onSelectedAgentChange(agentId)
                                isToolsExpanded = toolsExpandedBeforeDropdown
                                showDropdown = false
                            },
                    contentAlignment = Alignment.Center
                ) {
                    Image(
                        painter = painterResource(id = logoRes),
                        contentDescription = agentId,
                        modifier = Modifier.size(36.dp),
                        contentScale = ContentScale.Fit
                    )
                }
            }
            
            // Center - standard agent button (click to close dropdown)
            Box(modifier = Modifier.align(if (isSnappedRight) Alignment.CenterEnd else Alignment.CenterStart)) {
                AgentCircleButton(
                    selectedAgent = selectedAgent,
                    isRecording = isRecording,
                    onDragStart = onDragStart,
                    onDrag = onDrag,
                    onDragEnd = onDragEnd,
                    onToggleExpand = { showDropdown = false }, // Clicking center closes agent selection
                    onShowDropdown = { }, 
                    isToolsExpanded = true // Visual consistency
                )
            }
        }
    }

    // ============ JOBS BOTTOM SHEET ============
    if (showJobsSheet) {
            ModalBottomSheet(
                onDismissRequest = { onDismissJobsSheet() },
                containerColor = NeuroColors.GlassPrimary
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text(
                        text = "Saved Jobs",
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = androidx.compose.ui.text.font.FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    if (jobsList.isEmpty()) {
                        Text(
                            text = "No jobs saved yet.\nUse Start Capture to save job descriptions.",
                            color = NeuroColors.TextMuted,
                            fontSize = 14.sp
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier.heightIn(max = 400.dp)
                        ) {
                            items(jobsList) { job ->
                                JobItem(job = job)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(32.dp))
                }
            }
        }

        // ============ CHAT PANEL (FLOATING) ============
        if (showChatPanel) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    color = Color(0xDD1A1A1A),
                    shape = RoundedCornerShape(16.dp),
                    shadowElevation = 8.dp,
                    modifier = Modifier.fillMaxWidth(0.85f).fillMaxHeight(0.7f)
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp)
                    ) {
                        // Agent header
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Agent logo
                            val logoRes = when (selectedAgent) {
                                "neuro" -> R.drawable.logo
                                "openclaw" -> R.drawable.openclaw_logo
                                "opencode" -> R.drawable.opencode_logo
                                else -> R.drawable.logo
                            }
                            Image(
                                painter = painterResource(id = logoRes),
                                contentDescription = selectedAgent,
                                modifier = Modifier.size(32.dp),
                                contentScale = ContentScale.Fit
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = when (selectedAgent) {
                                        "neuro" -> "Neuro"
                                        "openclaw" -> "OpenClaw"
                                        "opencode" -> "OpenCode"
                                        else -> selectedAgent.replaceFirstChar { it.uppercase() }
                                    },
                                    color = Color.White,
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "Chat",
                                    color = Color.White.copy(alpha = 0.6f),
                                    fontSize = 12.sp
                                )
                            }
                            Spacer(modifier = Modifier.weight(1f))
                            Icon(
                                imageVector = Icons.Default.History,
                                contentDescription = "Chat history",
                                tint = Color.White,
                                modifier = Modifier
                                    .size(24.dp)
                                    .clickable { onShowHistory() }
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Close chat",
                                tint = Color.White,
                                modifier = Modifier
                                    .size(24.dp)
                                    .clickable { onChatToggle() }
                            )
                        }

                        HorizontalDivider(color = Color(0xFF3A3A3A), modifier = Modifier.padding(vertical = 8.dp))

                        // Show history list or tabs based on state
                        if (showChatHistory) {
                            // History list header
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                    contentDescription = "Back",
                                    tint = Color.White,
                                    modifier = Modifier
                                        .size(24.dp)
                                        .clickable { onDismissHistory() }
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Text(
                                    text = "Chat History",
                                    color = Color.White,
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            
                            HorizontalDivider(color = Color(0xFF3A3A3A), modifier = Modifier.padding(vertical = 8.dp))
                            
                            // History list
                            LazyColumn(
                                modifier = Modifier
                                    .weight(1f)
                                    .fillMaxWidth()
                            ) {
                                items(chatHistoryList) { item ->
                                    Surface(
                                        color = Color.Transparent,
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { onOpenChatFromHistory(item.cid, item.title) }
                                            .padding(vertical = 8.dp)
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.ChatBubbleOutline,
                                                contentDescription = null,
                                                tint = Color.White.copy(alpha = 0.7f),
                                                modifier = Modifier.size(20.dp)
                                            )
                                            Spacer(modifier = Modifier.width(12.dp))
                                            Column {
                                                Text(
                                                    text = item.title,
                                                    color = Color.White,
                                                    fontSize = 14.sp
                                                )
                                                Text(
                                                    text = item.cid.take(20) + "...",
                                                    color = Color.White.copy(alpha = 0.5f),
                                                    fontSize = 10.sp
                                                )
                                            }
                                        }
                                    }
                                    HorizontalDivider(color = Color(0xFF3A3A3A), modifier = Modifier.padding(vertical = 4.dp))
                                }
                            }
                        } else {
                            // Tabs row
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.Start,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                // Tabs scrollable area
                                Row(
                                    modifier = Modifier
                                        .weight(1f)
                                        .horizontalScroll(rememberScrollState()),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    chatTabs.forEach { tab ->
                                        ChatTabItem(
                                            title = tab.title,
                                            isActive = tab.cid == activeTabCid,
                                            onSelect = { onTabSelect(tab.cid) },
                                            onClose = { onTabClose(tab.cid) }
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                    }
                                    // New tab button
                                    Surface(
                                        color = Color.Transparent,
                                        shape = RoundedCornerShape(6.dp),
                                        modifier = Modifier
                                            .size(32.dp)
                                            .clickable { onNewTab() }
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Icon(
                                                imageVector = Icons.Default.Add,
                                                contentDescription = "New tab",
                                                tint = Color.White,
                                                modifier = Modifier.size(20.dp)
                                            )
                                        }
                                    }
                                }
                            }

                            HorizontalDivider(color = Color(0xFF3A3A3A), modifier = Modifier.padding(vertical = 8.dp))

                            // Messages
                            LazyColumn(
                                modifier = Modifier
                                    .weight(1f)
                                    .fillMaxWidth()
                            ) {
                                items(chatMessages) { msg ->
                                    val isUser = msg["isUser"] as? Boolean ?: false
                                    val text = msg["text"] as? String ?: ""
                                    ChatMessageBubble(text = text, isUser = isUser)
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Input row
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            BasicTextField(
                                value = chatInputText,
                                onValueChange = onChatInputChange,
                                modifier = Modifier
                                    .weight(1f)
                                    .background(NeuroColors.BackgroundMid, RoundedCornerShape(20.dp))
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                textStyle = androidx.compose.ui.text.TextStyle(color = Color.White, fontSize = 14.sp),
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(imeAction = androidx.compose.ui.text.input.ImeAction.Send),
                                keyboardActions = KeyboardActions(onSend = { onChatSend() })
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Icon(
                                imageVector = Icons.Default.Send,
                                contentDescription = "Send",
                                tint = NeuroColors.Primary,
                                modifier = Modifier
                                    .size(32.dp)
                                    .clickable { onChatSend() }
                            )
                        }
                    }
                }
            }
	    }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AgentCircleButton(
    selectedAgent: String,
    isRecording: Boolean,
    onDragStart: () -> Unit = {},
    onDrag: (Float, Float) -> Unit,
    onDragEnd: () -> Unit,
    onToggleExpand: () -> Unit,
    onShowDropdown: () -> Unit,
    isToolsExpanded: Boolean
) {
    Surface(
        color = if (isRecording) Color(0xFFEF4444) else Color(0xDD1A1A1A),
        shape = CircleShape,
        modifier = Modifier
            .size(56.dp)
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { onDragStart() },
                    onDrag = { change, dragAmount ->
                        change.consume()
                        onDrag(dragAmount.x, dragAmount.y)
                    },
                    onDragEnd = onDragEnd,
                    onDragCancel = onDragEnd
                )
            }
            .combinedClickable(
                onClick = onToggleExpand,
                onLongClick = onShowDropdown
            )
    ) {
        val logoRes = when (selectedAgent) {
            "neuro" -> R.drawable.logo
            "openclaw" -> R.drawable.openclaw_logo
            "opencode" -> R.drawable.opencode_logo
            "neuroupwork" -> R.drawable.upwork_logo
            else -> R.drawable.logo
        }
        Box(contentAlignment = Alignment.Center) {
            Image(
                painter = painterResource(id = logoRes),
                contentDescription = selectedAgent,
                modifier = Modifier.size(32.dp),
                contentScale = ContentScale.Fit
            )
        }
    }
}

@Composable
fun JobItem(job: Map<String, Any>) {
    val title = job["title"] as? String ?: "Unknown"
    val company = job["company"] as? String ?: ""
    val budget = job["budget"] as? String ?: ""
    val verdict = job["verdict"] as? String ?: ""

    Surface(
        color = NeuroColors.GlassPrimary.copy(alpha = 0.5f),
        shape = RoundedCornerShape(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp)
        ) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = androidx.compose.ui.text.font.FontWeight.Medium
            )
            if (company.isNotEmpty()) {
                Text(
                    text = company,
                    color = NeuroColors.TextMuted,
                    fontSize = 12.sp
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                if (budget.isNotEmpty()) {
                    Text(
                        text = budget,
                        color = NeuroColors.Primary,
                        fontSize = 12.sp
                    )
                }
                if (verdict.isNotEmpty()) {
                    Text(
                        text = verdict,
                        color = when (verdict) {
                            "worth_apply" -> Color(0xFF4CAF50)
                            "skip" -> Color(0xFFF44336)
                            else -> NeuroColors.TextMuted
                        },
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}

@Composable
fun ChatMessageBubble(text: String, isUser: Boolean) {
    Surface(
        color = if (isUser) NeuroColors.Primary.copy(alpha = 0.3f) else NeuroColors.GlassPrimary,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Text(
            text = text,
            color = if (isUser) NeuroColors.Primary else Color.White,
            fontSize = 14.sp,
            modifier = Modifier.padding(10.dp)
        )
    }
}

@Composable
fun DropdownItem(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Surface(
        color = if (isSelected) NeuroColors.Primary.copy(alpha = 0.3f) else Color.Transparent,
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        Text(
            text = text,
            color = if (isSelected) NeuroColors.Primary else Color.White,
            fontSize = 14.sp
        )
    }
}

@Composable
fun CircleToolButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    isActive: Boolean = false,
    onClick: () -> Unit
) {
    Surface(
        color = if (isActive) Color(0xFFEF4444) else Color(0xDD1A1A1A),
        shape = CircleShape,
        modifier = Modifier.size(44.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .clickable { onClick() },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(22.dp)
            )
        }
    }
}

@Composable
private fun ChatTabItem(
    title: String,
    isActive: Boolean,
    onSelect: () -> Unit,
    onClose: () -> Unit
) {
    var showConfirmDialog by remember { mutableStateOf(false) }
    val backgroundColor = if (isActive) Color(0xFF8B5CF6) else Color(0xFF2A2A2A)
    val textColor = Color.White
    val borderColor = if (isActive) Color(0xFF8B5CF6) else Color(0xFF3A3A3A)

    if (showConfirmDialog) {
        // Inline confirmation instead of AlertDialog
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .height(36.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(Color(0xFF3A3A3A))
                .padding(horizontal = 8.dp)
        ) {
            Text(
                text = "Close?",
                color = Color.White,
                fontSize = 12.sp
            )
            Spacer(modifier = Modifier.width(8.dp))
            TextButton(
                onClick = {
                    showConfirmDialog = false
                    onClose()
                },
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
            ) {
                Text("Yes", color = NeuroColors.Error, fontSize = 12.sp)
            }
            Text(
                text = "/",
                color = Color.White.copy(alpha = 0.5f),
                fontSize = 12.sp
            )
            TextButton(
                onClick = { showConfirmDialog = false },
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
            ) {
                Text("No", color = Color.White, fontSize = 12.sp)
            }
        }
    } else {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .height(36.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(backgroundColor)
                .border(1.dp, borderColor, RoundedCornerShape(6.dp))
                .clickable { onSelect() }
                .padding(horizontal = 10.dp)
        ) {
            Text(
                text = title.ifEmpty { "New Chat" },
                color = textColor,
                fontSize = 13.sp,
                fontWeight = if (isActive) FontWeight.Medium else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.widthIn(max = 120.dp)
            )

            Spacer(modifier = Modifier.width(6.dp))

            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Close tab",
                tint = textColor.copy(alpha = 0.7f),
                modifier = Modifier
                    .size(16.dp)
                    .clickable { showConfirmDialog = true }
            )
        }
    }
}
