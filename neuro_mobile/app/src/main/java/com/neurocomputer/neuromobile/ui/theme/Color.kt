package com.neurocomputer.neuromobile.ui.theme

import androidx.compose.ui.graphics.Color

// Neuro Black & White Glass Theme
object NeuroColors {
    // Backgrounds
    val BackgroundDark = Color(0xFF000000)
    val BackgroundMid = Color(0xFF0A0A0A)
    val BackgroundLight = Color(0xFF141414)

    // Glass surfaces
    val GlassPrimary = Color(0x14FFFFFF)
    val GlassSecondary = Color(0x0DFFFFFF)
    val GlassAccent = Color(0x1FFFFFFF)

    // User/Assistant bubbles
    val GlassUserBubble = Color(0x26FFFFFF)
    val GlassAssistantBubble = Color(0x08FFFFFF)

    // Borders
    val BorderLight = Color(0x26FFFFFF)
    val BorderSubtle = Color(0x14FFFFFF)
    val BorderAccent = Color(0x40FFFFFF)

    // Text
    val TextPrimary = Color(0xFFFFFFFF)
    val TextSecondary = Color(0xB3FFFFFF)
    val TextMuted = Color(0x80FFFFFF)
    val TextDim = Color(0x59FFFFFF)

    // Accent colors
    val Primary = Color(0xFF8B5CF6)     // Purple
    val Success = Color(0xFF4CAF50)     // Green
    val Error = Color(0xFFF44336)        // Red

    // Overlay
    val OverlayDark = Color(0xB3000000)
    val OverlayLight = Color(0x05FFFFFF)

    // Markdown code blocks
    val CodeBlockBackground = Color(0xFF1E1E2E)
    val CodeBlockBorder = Color(0xFF313244)
    val CodeBlockHeaderBackground = Color(0xFF181825)

    // Diff highlights
    val DiffAddedBackground = Color(0x2244CC44)
    val DiffAddedText = Color(0xFF88FF88)
    val DiffRemovedBackground = Color(0x22CC4444)
    val DiffRemovedText = Color(0xFFFF8888)

    // Syntax highlighting (Catppuccin-inspired)
    val SyntaxDefault = Color(0xFFCDD6F4)
    val SyntaxComment = Color(0xFF6C7086)
    val SyntaxString = Color(0xFFA6E3A1)
    val SyntaxKeyword = Color(0xFFCBA6F7)
    val SyntaxFunction = Color(0xFF89B4FA)
    val SyntaxNumber = Color(0xFFFAB387)
    val SyntaxType = Color(0xFF89DCEB)

    // Markdown misc
    val TableBorder = Color(0xFF313244)
    val HorizontalRuleColor = Color(0xFF45475A)
    val InlineCodeBackground = Color(0xFF1E1E2E)
    val LinkColor = Color(0xFF89B4FA)

    // More markdown
    val DiffHunkText = Color(0xFF6C7086)
    val BlockquoteBorder = Color(0xFF6C7086)
    val BlockquoteBackground = Color(0xFF1E1E2E)
    val TableHeaderBackground = Color(0xFF181825)

    // Glow / border variants
    val PrimaryGlow = Color(0x408B5CF6)
    val PrimaryBorderMid = Color(0x608B5CF6)
}
