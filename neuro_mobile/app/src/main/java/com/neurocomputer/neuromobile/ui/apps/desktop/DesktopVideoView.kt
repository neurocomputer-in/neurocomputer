package com.neurocomputer.neuromobile.ui.apps.desktop

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import io.livekit.android.compose.ui.VideoTrackView
import io.livekit.android.room.track.VideoTrack

@Composable
fun DesktopVideoView(
    videoTrack: VideoTrack?,
    modifier: Modifier = Modifier,
) {
    Box(modifier.fillMaxSize().background(Color.Black)) {
        if (videoTrack != null) {
            VideoTrackView(
                videoTrack = videoTrack,
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}
