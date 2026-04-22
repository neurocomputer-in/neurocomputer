package com.neurocomputer.neuromobile.ui.components

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import org.json.JSONObject

data class WindowApp(
    val windowClass: String,
    val displayClass: String,
    val windows: List<WindowInfo>
)

data class WindowInfo(
    val id: String,
    val title: String,
    val windowClass: String
)

@Composable
fun WindowSelectorOverlay(
    baseUrl: String,
    onExit: () -> Unit,
    onWindowSelected: (String) -> Unit
) {
    var apps by remember { mutableStateOf<List<WindowApp>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var screenshots by remember { mutableStateOf<Map<String, Bitmap>>(emptyMap()) }
    var longPressedApp by remember { mutableStateOf<WindowApp?>(null) }
    val scope = rememberCoroutineScope()

    val httpClient = remember {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()
    }

    fun loadScreenshot(windowId: String) {
        if (screenshots.containsKey(windowId)) return
        scope.launch {
            try {
                withContext(Dispatchers.IO) {
                    val request = Request.Builder()
                        .url("$baseUrl/windows/$windowId/screenshot")
                        .get()
                        .build()
                    httpClient.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            val body = response.body?.string() ?: ""
                            val json = JSONObject(body)
                            val base64 = json.getString("screenshot")
                            val bytes = Base64.decode(base64, Base64.DEFAULT)
                            val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                            if (bitmap != null) {
                                withContext(Dispatchers.Main) {
                                    screenshots = screenshots + (windowId to bitmap)
                                }
                            }
                        }
                    }
                }
            } catch (_: Exception) {}
        }
    }

    fun focusWindow(windowId: String) {
        scope.launch {
            try {
                withContext(Dispatchers.IO) {
                    val request = Request.Builder()
                        .url("$baseUrl/windows/$windowId/focus")
                        .post("{}".toRequestBody("application/json".toMediaType()))
                        .build()
                    httpClient.newCall(request).execute().close()
                }
                onWindowSelected(windowId)
                onExit()
            } catch (_: Exception) {
                onExit()
            }
        }
    }

    LaunchedEffect(Unit) {
        loading = true
        error = null
        try {
            withContext(Dispatchers.IO) {
                val request = Request.Builder()
                    .url("$baseUrl/windows")
                    .get()
                    .build()
                httpClient.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string() ?: "{}"
                        val json = JSONObject(body)
                        val appsArray = json.getJSONArray("apps")
                        val appList = mutableListOf<WindowApp>()
                        for (i in 0 until appsArray.length()) {
                            val appJson = appsArray.getJSONObject(i)
                            val windowsArray = appJson.getJSONArray("windows")
                            val windows = mutableListOf<WindowInfo>()
                            for (j in 0 until windowsArray.length()) {
                                val winJson = windowsArray.getJSONObject(j)
                                windows.add(WindowInfo(
                                    id = winJson.getString("id"),
                                    title = winJson.getString("title"),
                                    windowClass = winJson.getString("windowClass")
                                ))
                            }
                            appList.add(WindowApp(
                                windowClass = appJson.getString("class"),
                                displayClass = appJson.getString("displayClass"),
                                windows = windows
                            ))
                        }
                        withContext(Dispatchers.Main) {
                            apps = appList
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            error = "Failed to load windows: ${response.code}"
                        }
                    }
                }
            }
        } catch (e: Exception) {
            error = e.message ?: "Unknown error"
        } finally {
            loading = false
        }
    }

    // Preload top window screenshot for each app once apps load
    LaunchedEffect(apps) {
        apps.forEach { app ->
            app.windows.firstOrNull()?.let { loadScreenshot(it.id) }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xEE0A0A0F))
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .padding(horizontal = 12.dp)
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Windows",
                        color = Color.White,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold
                    )
                    if (apps.isNotEmpty()) {
                        Text(
                            text = "${apps.sumOf { it.windows.size }} open · ${apps.size} apps",
                            color = Color.White.copy(alpha = 0.4f),
                            fontSize = 11.sp
                        )
                    }
                }
                IconButton(
                    onClick = onExit,
                    modifier = Modifier
                        .size(36.dp)
                        .background(Color.White.copy(alpha = 0.08f), CircleShape)
                ) {
                    Icon(Icons.Default.Close, contentDescription = "Close", tint = Color.White, modifier = Modifier.size(18.dp))
                }
            }

            when {
                loading -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator(color = NeuroColors.Primary, strokeWidth = 2.dp)
                            Spacer(Modifier.height(12.dp))
                            Text("Loading windows…", color = Color.White.copy(alpha = 0.5f), fontSize = 12.sp)
                        }
                    }
                }
                error != null -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(text = error ?: "Error", color = NeuroColors.Error, fontSize = 13.sp)
                    }
                }
                apps.isEmpty() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("No windows found", color = Color.White.copy(alpha = 0.4f), fontSize = 13.sp)
                    }
                }
                else -> {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(3),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 16.dp)
                    ) {
                        items(apps) { app ->
                            AppGroupCard(
                                app = app,
                                topScreenshot = screenshots[app.windows.first().id],
                                onTap = { focusWindow(app.windows.first().id) },
                                onLongPress = {
                                    // Preload all window screenshots for this app
                                    app.windows.forEach { loadScreenshot(it.id) }
                                    longPressedApp = app
                                }
                            )
                        }
                    }
                }
            }
        }

        // Long-press app windows sheet
        longPressedApp?.let { app ->
            AppWindowsSheet(
                app = app,
                screenshots = screenshots,
                onDismiss = { longPressedApp = null },
                onWindowTap = { windowId ->
                    longPressedApp = null
                    focusWindow(windowId)
                }
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun AppGroupCard(
    app: WindowApp,
    topScreenshot: Bitmap?,
    onTap: () -> Unit,
    onLongPress: () -> Unit
) {
    val appIcon = getAppIcon(app.displayClass)
    val hasMultiple = app.windows.size > 1

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1.7f)
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0xFF13131F))
            .combinedClickable(
                onClick = onTap,
                onLongClick = onLongPress
            )
    ) {
        // Screenshot fill
        if (topScreenshot != null) {
            Image(
                bitmap = topScreenshot.asImageBitmap(),
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        } else {
            Box(
                modifier = Modifier.fillMaxSize().background(Color(0xFF0E0E1A)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    appIcon,
                    contentDescription = null,
                    tint = Color.White.copy(alpha = 0.12f),
                    modifier = Modifier.size(22.dp)
                )
            }
        }

        // Thin top accent line
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(2.dp)
                .align(Alignment.TopCenter)
                .background(
                    Brush.horizontalGradient(
                        colors = listOf(
                            Color.Transparent,
                            NeuroColors.Primary.copy(alpha = 0.7f),
                            Color.Transparent
                        )
                    )
                )
        )

        // Bottom label strip
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(Color(0xCC0A0A14))
                .padding(horizontal = 6.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                appIcon,
                contentDescription = null,
                tint = NeuroColors.Primary.copy(alpha = 0.8f),
                modifier = Modifier.size(9.dp)
            )
            Spacer(Modifier.width(4.dp))
            Text(
                text = app.displayClass,
                color = Color.White.copy(alpha = 0.9f),
                fontSize = 9.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            if (hasMultiple) {
                Spacer(Modifier.width(4.dp))
                Box(
                    modifier = Modifier
                        .defaultMinSize(minWidth = 14.dp, minHeight = 14.dp)
                        .clip(RoundedCornerShape(7.dp))
                        .background(NeuroColors.Primary.copy(alpha = 0.85f))
                        .padding(horizontal = 3.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${app.windows.size}",
                        color = Color.White,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Thin outer border overlay
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawRoundRect(
                color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.1f),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()),
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = 1f)
            )
        }

        // Loading indicator dot
        if (topScreenshot == null) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(4.dp)
                    .size(5.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.2f))
            )
        }
    }
}

@Composable
private fun AppWindowsSheet(
    app: WindowApp,
    screenshots: Map<String, Bitmap>,
    onDismiss: () -> Unit,
    onWindowTap: (String) -> Unit
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.6f)),
            contentAlignment = Alignment.BottomCenter
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp))
                    .background(Color(0xFF12121E))
                    .padding(bottom = 24.dp)
            ) {
                // Handle bar
                Box(
                    modifier = Modifier
                        .align(Alignment.CenterHorizontally)
                        .padding(top = 10.dp, bottom = 14.dp)
                        .size(36.dp, 4.dp)
                        .clip(CircleShape)
                        .background(Color.White.copy(alpha = 0.2f))
                )

                // App header
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        getAppIcon(app.displayClass),
                        contentDescription = null,
                        tint = NeuroColors.Primary,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = app.displayClass,
                        color = Color.White,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "${app.windows.size} windows",
                        color = Color.White.copy(alpha = 0.4f),
                        fontSize = 11.sp
                    )
                    Spacer(Modifier.weight(1f))
                    IconButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .size(32.dp)
                            .background(Color.White.copy(alpha = 0.08f), CircleShape)
                    ) {
                        Icon(
                            Icons.Default.ArrowBack,
                            contentDescription = "Back to all windows",
                            tint = Color.White.copy(alpha = 0.7f),
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                Spacer(Modifier.height(12.dp))

                // Horizontal scrolling window thumbnails
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    contentPadding = PaddingValues(horizontal = 16.dp)
                ) {
                    items(app.windows) { window ->
                        WindowThumbnailCard(
                            window = window,
                            screenshot = screenshots[window.id],
                            onTap = { onWindowTap(window.id) }
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun WindowThumbnailCard(
    window: WindowInfo,
    screenshot: Bitmap?,
    onTap: () -> Unit
) {
    Column(
        modifier = Modifier.width(140.dp),
        horizontalAlignment = Alignment.Start
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(90.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF1A1A2A))
                .combinedClickable(onClick = onTap),
            contentAlignment = Alignment.Center
        ) {
            if (screenshot != null) {
                Image(
                    bitmap = screenshot.asImageBitmap(),
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            } else {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = NeuroColors.Primary,
                    strokeWidth = 2.dp
                )
            }
        }
        Spacer(Modifier.height(5.dp))
        Text(
            text = window.title.ifEmpty { "Window" },
            color = Color.White.copy(alpha = 0.8f),
            fontSize = 10.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            lineHeight = 13.sp,
            modifier = Modifier.padding(horizontal = 2.dp)
        )
    }
}

private fun getAppIcon(displayClass: String): androidx.compose.ui.graphics.vector.ImageVector {
    return when {
        displayClass.contains("chrome", ignoreCase = true) ||
        displayClass.contains("firefox", ignoreCase = true) ||
        displayClass.contains("browser", ignoreCase = true) -> Icons.Default.Language

        displayClass.contains("terminal", ignoreCase = true) ||
        displayClass.contains("konsole", ignoreCase = true) ||
        displayClass.contains("xterm", ignoreCase = true) -> Icons.Default.Terminal

        displayClass.contains("nautilus", ignoreCase = true) ||
        displayClass.contains("files", ignoreCase = true) ||
        displayClass.contains("thunar", ignoreCase = true) -> Icons.Default.Folder

        displayClass.contains("windsurf", ignoreCase = true) ||
        displayClass.contains("code", ignoreCase = true) ||
        displayClass.contains("vscode", ignoreCase = true) ||
        displayClass.contains("sublime", ignoreCase = true) -> Icons.Default.Code

        displayClass.contains("gedit", ignoreCase = true) ||
        displayClass.contains("notepad", ignoreCase = true) ||
        displayClass.contains("text", ignoreCase = true) -> Icons.Default.Description

        displayClass.contains("anydesk", ignoreCase = true) ||
        displayClass.contains("teamviewer", ignoreCase = true) -> Icons.Default.DesktopWindows

        displayClass.contains("settings", ignoreCase = true) ||
        displayClass.contains("preferences", ignoreCase = true) -> Icons.Default.Settings

        displayClass.contains("vlc", ignoreCase = true) ||
        displayClass.contains("video", ignoreCase = true) ||
        displayClass.contains("media", ignoreCase = true) -> Icons.Default.PlayCircle

        else -> Icons.Default.Window
    }
}
