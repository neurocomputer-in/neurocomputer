package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.AppId

@Composable
fun MobileDock(
    dockPins: List<AppId>,
    onLaunch: (AppId) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(
                Color(0x99111118),
                RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
            )
            .windowInsetsPadding(WindowInsets.navigationBars)
            .padding(horizontal = 24.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        dockPins.forEach { appId ->
            val app = APP_MAP[appId] ?: return@forEach
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(app.color.copy(alpha = 0.85f), RoundedCornerShape(14.dp))
                    .clickable { onLaunch(appId) },
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    app.icon,
                    contentDescription = app.name,
                    tint = Color.White,
                    modifier = Modifier.size(26.dp),
                )
            }
        }
    }
}
