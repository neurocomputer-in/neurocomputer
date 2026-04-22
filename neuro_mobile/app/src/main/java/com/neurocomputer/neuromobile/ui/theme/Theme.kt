package com.neurocomputer.neuromobile.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val NeuroDarkColorScheme = darkColorScheme(
    primary = NeuroColors.Primary,
    onPrimary = NeuroColors.BackgroundDark,
    secondary = NeuroColors.TextSecondary,
    onSecondary = NeuroColors.BackgroundDark,
    tertiary = NeuroColors.TextMuted,
    background = NeuroColors.BackgroundDark,
    onBackground = NeuroColors.TextPrimary,
    surface = NeuroColors.GlassPrimary,
    onSurface = NeuroColors.TextPrimary,
    surfaceVariant = NeuroColors.GlassSecondary,
    onSurfaceVariant = NeuroColors.TextSecondary,
    outline = NeuroColors.BorderSubtle,
    outlineVariant = NeuroColors.BorderLight,
    error = NeuroColors.Error,
    onError = NeuroColors.BackgroundDark
)

@Composable
fun NeuroTheme(
    content: @Composable () -> Unit
) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = NeuroColors.BackgroundDark.toArgb()
            window.navigationBarColor = NeuroColors.BackgroundDark.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = false
                isAppearanceLightNavigationBars = false
            }
        }
    }

    MaterialTheme(
        colorScheme = NeuroDarkColorScheme,
        typography = NeuroTypography,
        content = content
    )
}
