package com.neurocomputer.neuromobile.ui.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.data.APP_LIST
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.ui.components.AppIcon

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppPicker(
    onPick: (AppId) -> Unit,
    onDismiss: () -> Unit,
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF111118),
    ) {
        LazyVerticalGrid(
            columns = GridCells.Fixed(4),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 480.dp),
        ) {
            items(APP_LIST.size) { index ->
                val app = APP_LIST[index]
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .clickable { onPick(app.id) }
                        .padding(vertical = 4.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .size(52.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(
                                if (app.iconResId != null) Color.Transparent
                                else app.color.copy(alpha = 0.9f)
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        AppIcon(app = app, size = if (app.iconResId != null) 52.dp else 32.dp)
                    }
                    Spacer(Modifier.height(5.dp))
                    Text(
                        app.name,
                        color = Color.White.copy(alpha = 0.85f),
                        fontSize = 10.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}
