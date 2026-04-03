package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.R
import com.neurocomputer.neuromobile.domain.model.AgentInfo
import com.neurocomputer.neuromobile.domain.model.AgentType
import com.neurocomputer.neuromobile.ui.theme.NeuroColors

import androidx.compose.ui.unit.DpOffset

@Composable
fun AgentDropdown(
    agents: List<AgentInfo>,
    selectedAgent: AgentInfo,
    onSelect: (AgentInfo) -> Unit,
    onDismiss: () -> Unit,
    menuAlignment: Alignment = Alignment.TopStart,
    menuOffset: DpOffset = DpOffset(60.dp, 110.dp)
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.3f))
            .clickable { onDismiss() }
    ) {
        Box(
            modifier = Modifier
                .align(menuAlignment)
                .offset(x = menuOffset.x, y = menuOffset.y)
                .widthIn(max = 200.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(NeuroColors.BackgroundMid)
                .clickable(enabled = false) { }
        ) {
            Column(
                modifier = Modifier.padding(8.dp)
            ) {
                agents.forEach { agent ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable { onSelect(agent) }
                            .background(
                                if (agent == selectedAgent) NeuroColors.GlassPrimary else Color.Transparent
                            )
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Agent logo
                        Box(
                            modifier = Modifier.size(24.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            when (agent.type) {
                                AgentType.NEURO -> Image(
                                    painter = painterResource(id = R.drawable.logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.OPENCLAW -> Image(
                                    painter = painterResource(id = R.drawable.openclaw_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.OPENCODE -> Image(
                                    painter = painterResource(id = R.drawable.opencode_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.NEUROUPWORK -> Image(
                                    painter = painterResource(id = R.drawable.upwork_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(10.dp))

                        Text(
                            text = agent.name,
                            color = NeuroColors.TextPrimary,
                            fontSize = 14.sp,
                            modifier = Modifier.weight(1f)
                        )

                        if (agent == selectedAgent) {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = "Selected",
                                tint = NeuroColors.Primary,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}
