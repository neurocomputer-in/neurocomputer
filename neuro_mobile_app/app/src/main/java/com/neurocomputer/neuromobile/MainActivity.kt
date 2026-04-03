package com.neurocomputer.neuromobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.repository.StartupRepository
import com.neurocomputer.neuromobile.ui.screens.MainScreen
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import com.neurocomputer.neuromobile.ui.theme.NeuroTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var backendUrlRepository: BackendUrlRepository

    @Inject
    lateinit var startupRepository: StartupRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Initialize backend URL (probe WiFi, fallback to ngrok), then mark ready
        lifecycleScope.launch {
            backendUrlRepository.init()
            startupRepository.setInitialized()
        }

        setContent {
            val isInitialized by startupRepository.isInitialized.collectAsState()

            NeuroTheme {
                if (isInitialized) {
                    Surface(
                        modifier = Modifier.fillMaxSize(),
                        color = NeuroColors.BackgroundDark
                    ) {
                        MainScreen()
                    }
                } else {
                    // Loading screen while backend URL is being resolved
                    Surface(
                        modifier = Modifier.fillMaxSize(),
                        color = NeuroColors.BackgroundDark
                    ) {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator(
                                    color = NeuroColors.Primary,
                                    modifier = Modifier.size(40.dp)
                                )
                                Spacer(modifier = Modifier.height(16.dp))
                                Text(
                                    text = "Connecting...",
                                    color = NeuroColors.TextMuted,
                                    fontSize = 14.sp
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

