package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import com.neurocomputer.neuromobile.data.AppDef

/**
 * Renders an app's branded PNG when [AppDef.iconResId] is set, otherwise falls
 * back to its Material vector icon. Tile composables (HomeScreen, Dock,
 * AppPicker, AppSwitcher, MobileTabStrip, MobileControlSheet) go through this
 * so we don't have to duplicate the painter-vs-icon branch in five places.
 */
@Composable
fun AppIcon(
    app: AppDef,
    size: Dp,
    modifier: Modifier = Modifier,
    tint: Color = Color.White,
) {
    val resId = app.iconResId
    if (resId != null) {
        Image(
            painter = painterResource(id = resId),
            contentDescription = app.name,
            modifier = modifier.size(size),
            contentScale = ContentScale.Fit,
        )
    } else {
        Icon(
            imageVector = app.icon,
            contentDescription = app.name,
            tint = tint,
            modifier = modifier.size(size),
        )
    }
}
