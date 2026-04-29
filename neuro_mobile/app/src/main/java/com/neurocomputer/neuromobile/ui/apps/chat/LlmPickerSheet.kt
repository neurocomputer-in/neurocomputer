package com.neurocomputer.neuromobile.ui.apps.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LlmPickerSheet(
    currentProvider: String,
    currentModel: String,
    providers: List<LlmProviderInfo>,
    onDismiss: () -> Unit,
    onConfirm: (provider: String, model: String) -> Unit,
) {
    var selectedProvider by remember(currentProvider) { mutableStateOf(currentProvider) }
    var selectedModel by remember(currentModel) { mutableStateOf(currentModel) }

    val providerInfo = providers.find { it.id == selectedProvider }
    val availableModels = providerInfo?.models ?: emptyList()

    // Reset model when provider changes if current model isn't in new provider's list
    LaunchedEffect(selectedProvider) {
        if (selectedModel !in availableModels && providerInfo != null) {
            selectedModel = providerInfo.defaultModel
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1a1a2e),
        dragHandle = { BottomSheetDefaults.DragHandle(color = Color(0xFF4a4a6a)) },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp),
        ) {
            Text(
                text = "Provider & Model",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                modifier = Modifier.padding(bottom = 20.dp),
            )

            Text(
                text = "Provider",
                fontSize = 12.sp,
                color = Color(0xFF8888aa),
                modifier = Modifier.padding(bottom = 8.dp),
            )

            if (providers.isEmpty()) {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.CenterHorizontally).padding(16.dp),
                    color = Color(0xFF8B5CF6),
                    strokeWidth = 2.dp,
                )
            } else {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(bottom = 20.dp),
                ) {
                    providers.filter { it.available }.forEach { provider ->
                        val selected = provider.id == selectedProvider
                        Box(
                            modifier = Modifier
                                .border(
                                    1.dp,
                                    if (selected) Color(0xFF8B5CF6) else Color(0xFF3a3a5a),
                                    RoundedCornerShape(8.dp),
                                )
                                .background(
                                    if (selected) Color(0xFF8B5CF6).copy(alpha = 0.2f) else Color.Transparent,
                                    RoundedCornerShape(8.dp),
                                )
                                .clickable { selectedProvider = provider.id }
                                .padding(horizontal = 14.dp, vertical = 8.dp),
                        ) {
                            Text(
                                text = provider.name,
                                fontSize = 13.sp,
                                color = if (selected) Color(0xFFD4A8FF) else Color(0xFF8888aa),
                                fontWeight = if (selected) FontWeight.Medium else FontWeight.Normal,
                            )
                        }
                    }
                }

                Text(
                    text = "Model",
                    fontSize = 12.sp,
                    color = Color(0xFF8888aa),
                    modifier = Modifier.padding(bottom = 8.dp),
                )

                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 280.dp)
                        .background(Color(0xFF111120), RoundedCornerShape(12.dp))
                        .padding(vertical = 4.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    items(availableModels) { model ->
                        val selected = model == selectedModel
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { selectedModel = model }
                                .background(
                                    if (selected) Color(0xFF8B5CF6).copy(alpha = 0.15f) else Color.Transparent,
                                )
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                text = model,
                                fontSize = 13.sp,
                                color = if (selected) Color(0xFFD4A8FF) else Color(0xFFccccee),
                                fontWeight = if (selected) FontWeight.Medium else FontWeight.Normal,
                            )
                            if (selected) {
                                Text("✓", fontSize = 13.sp, color = Color(0xFF8B5CF6))
                            }
                        }
                    }
                }

                Spacer(Modifier.height(20.dp))

                Button(
                    onClick = { onConfirm(selectedProvider, selectedModel) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF8B5CF6)),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Text("Apply", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
