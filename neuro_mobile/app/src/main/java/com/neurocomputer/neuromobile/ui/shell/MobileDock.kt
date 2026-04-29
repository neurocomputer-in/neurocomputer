package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.ui.components.AppIcon

private const val MAX_DOCK_PINS = 4

@Composable
fun MobileDock(
    dockPins: List<AppId>,
    onLaunch: (AppId) -> Unit,
    onOpenLauncher: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(
                Color(0xFF0e0e16),
                RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
            )
            .windowInsetsPadding(WindowInsets.navigationBars)
            .padding(horizontal = 20.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val left = dockPins.take(2)
        val right = dockPins.drop(2).take(2)

        left.forEach { appId ->
            val app = APP_MAP[appId] ?: return@forEach
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(
                        if (app.iconResId != null) Color.Transparent
                        else app.color.copy(alpha = 0.85f)
                    )
                    .clickable { onLaunch(appId) },
                contentAlignment = Alignment.Center,
            ) {
                AppIcon(app = app, size = if (app.iconResId != null) 52.dp else 32.dp)
            }
        }

        // Launcher centered
        Box(
            modifier = Modifier
                .size(52.dp)
                .background(Color(0xFF2a2a3a), RoundedCornerShape(14.dp))
                .clickable { onOpenLauncher() },
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Default.Apps,
                contentDescription = "All Apps",
                tint = Color.White,
                modifier = Modifier.size(24.dp),
            )
        }

        right.forEach { appId ->
            val app = APP_MAP[appId] ?: return@forEach
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(
                        if (app.iconResId != null) Color.Transparent
                        else app.color.copy(alpha = 0.85f)
                    )
                    .clickable { onLaunch(appId) },
                contentAlignment = Alignment.Center,
            ) {
                AppIcon(app = app, size = if (app.iconResId != null) 52.dp else 32.dp)
            }
        }
    }
}
