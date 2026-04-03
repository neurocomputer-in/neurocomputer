package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.blur
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.domain.model.ConversationSummary
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

@Composable
fun ChatListItem(
    conversation: ConversationSummary,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(NeuroColors.GlassPrimary.copy(alpha = 0.3f))
            .clickable { onClick() }
    ) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .blur(10.dp)
                .background(NeuroColors.GlassPrimary.copy(alpha = 0.3f))
        )
        Column(
            modifier = Modifier.padding(12.dp)
        ) {
            // Title row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = conversation.title.ifEmpty { "New Chat" },
                    color = NeuroColors.TextPrimary,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )

                Text(
                    text = formatTimestamp(conversation.updatedAt),
                    color = NeuroColors.TextMuted,
                    fontSize = 11.sp
                )
            }

            if (conversation.lastMessage.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = conversation.lastMessage,
                    color = NeuroColors.TextMuted,
                    fontSize = 12.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

private fun formatTimestamp(isoTimestamp: String): String {
    // Simple formatting - just show time portion if today, or date if older
    // Format: "2026-03-30T14:30:00+00:00"
    return try {
        if (isoTimestamp.length >= 16) {
            isoTimestamp.substring(11, 16) // "HH:mm"
        } else {
            ""
        }
    } catch (e: Exception) {
        ""
    }
}
