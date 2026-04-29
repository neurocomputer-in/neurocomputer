package com.neurocomputer.neuromobile.ui.apps.desktop

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import io.livekit.android.compose.local.RoomLocal
import io.livekit.android.compose.ui.ScaleType
import io.livekit.android.compose.ui.VideoTrackView
import io.livekit.android.room.Room
import io.livekit.android.room.track.VideoTrack

/**
 * `VideoTrackView` from livekit-android-compose calls `requireRoom()` internally,
 * which reads from the `RoomLocal` CompositionLocal. We already manage the Room
 * lifecycle in `LiveKitService` (connects when the user taps Connect, holds the
 * subscribed video track), so we just need to provide it via the CompositionLocal
 * — using `RoomScope` would try to (re)connect with a different URL/token.
 */
@Composable
fun DesktopVideoView(
    room: Room?,
    videoTrack: VideoTrack?,
    modifier: Modifier = Modifier,
) {
    Box(modifier.fillMaxSize().background(Color.Black)) {
        if (room != null && videoTrack != null) {
            CompositionLocalProvider(RoomLocal provides room) {
                VideoTrackView(
                    videoTrack = videoTrack,
                    modifier = Modifier.fillMaxSize(),
                    // FitInside preserves the 1280×720 aspect ratio (letterbox)
                    // instead of cropping. With Fill the video gets cropped on
                    // sides that don't match phone landscape ratio → "zoomed-in"
                    // appearance with content cut off.
                    scaleType = ScaleType.FitInside,
                )
            }
        }
    }
}
