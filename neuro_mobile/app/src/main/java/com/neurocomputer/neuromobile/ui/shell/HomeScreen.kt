package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.APP_MAP
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.ui.components.AppIcon
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

@Composable
fun HomeScreen(
    iconOrder: List<AppId>,
    onLaunch: (AppId) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(4),
        modifier = modifier
            .fillMaxSize()
            .background(NeuroColors.BackgroundDark)
            .windowInsetsPadding(WindowInsets.statusBars),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        items(iconOrder, key = { it.name }) { appId ->
            val app = APP_MAP[appId] ?: return@items
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.clickable { onLaunch(appId) },
            ) {
                Box(
                    modifier = Modifier
                        .size(60.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(
                            if (app.iconResId != null) Color.Transparent
                            else app.color.copy(alpha = 0.85f)
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    AppIcon(app = app, size = if (app.iconResId != null) 60.dp else 36.dp)
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    app.name,
                    color = Color.White,
                    fontSize = 10.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
