package com.neurocomputer.neuromobile.ui.apps.ide

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IDEApp(cid: String, modifier: Modifier = Modifier) {
    val viewModel = hiltViewModel<IDEViewModel, IDEViewModel.Factory>(
        key = cid,
        creationCallback = { factory -> factory.create(cid) },
    )
    val state by viewModel.state.collectAsState()
    var zoom by remember { mutableFloatStateOf(1f) }
    var panOffset by remember { mutableStateOf(Offset.Zero) }

    Box(modifier.fillMaxSize().background(Color(0xFF0a0a12))) {
        if (state.isLoading) {
            CircularProgressIndicator(Modifier.align(Alignment.Center), color = Color(0xFF8B5CF6))
        } else if (state.errorMessage != null) {
            Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(state.errorMessage ?: "Error", color = Color(0xFFFF5555))
                Spacer(Modifier.height(8.dp))
                TextButton(onClick = viewModel::refresh) { Text("Retry", color = Color(0xFF8B5CF6)) }
            }
        }

        GraphCanvas(
            nodes = state.nodes,
            edges = state.edges,
            selectedNodeId = state.selectedNodeId,
            zoom = zoom,
            panOffset = panOffset,
            onZoomChange = { zoom = it },
            onPanChange = { panOffset = it },
            onNodeTap = { id -> viewModel.selectNode(if (id.isEmpty()) null else id) },
            onNodeDrag = viewModel::moveNode,
            modifier = Modifier.fillMaxSize(),
        )

        // Toolbar (top-right)
        GraphToolbar(
            onAddNode = viewModel::addNode,
            onZoomIn = { zoom = (zoom * 1.25f).coerceAtMost(5f) },
            onZoomOut = { zoom = (zoom / 1.25f).coerceAtLeast(0.2f) },
            onFitScreen = {
                zoom = 1f
                panOffset = Offset.Zero
            },
            modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
        )
    }

    // NodeEditor bottom sheet
    val selectedNode = state.nodes.find { it.id == state.selectedNodeId }
    if (selectedNode != null) {
        NodeEditorSheet(
            node = selectedNode,
            onLabelChange = { label -> viewModel.updateNodeLabel(selectedNode.id, label) },
            onDismiss = { viewModel.selectNode(null) },
        )
    }
}

@Composable
private fun GraphToolbar(
    onAddNode: () -> Unit,
    onZoomIn: () -> Unit,
    onZoomOut: () -> Unit,
    onFitScreen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        IconButton(
            onClick = onAddNode,
            colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF1e1e2e)),
        ) {
            Icon(Icons.Default.Add, contentDescription = "Add node", tint = Color(0xFF8B5CF6))
        }
        IconButton(
            onClick = onZoomIn,
            colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF1e1e2e)),
        ) {
            Icon(Icons.Default.ZoomIn, contentDescription = "Zoom in", tint = Color(0xFF8B5CF6))
        }
        IconButton(
            onClick = onZoomOut,
            colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF1e1e2e)),
        ) {
            Icon(Icons.Default.ZoomOut, contentDescription = "Zoom out", tint = Color(0xFF8B5CF6))
        }
        IconButton(
            onClick = onFitScreen,
            colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF1e1e2e)),
        ) {
            Icon(Icons.Default.FitScreen, contentDescription = "Fit screen", tint = Color(0xFF8B5CF6))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NodeEditorSheet(
    node: IdeNode,
    onLabelChange: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var labelText by remember(node.id) { mutableStateOf(node.label) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1e1e2e),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp).navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Edit Node", color = Color.White, fontSize = 16.sp)
            Text("ID: ${node.id}", color = Color(0xFF6B7280), fontSize = 12.sp)
            OutlinedTextField(
                value = labelText,
                onValueChange = { labelText = it },
                label = { Text("Label", color = Color(0xFF6B7280)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedBorderColor = Color(0xFF8B5CF6),
                    unfocusedBorderColor = Color(0xFF374151),
                ),
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                TextButton(onClick = onDismiss) {
                    Text("Cancel", color = Color(0xFF6B7280))
                }
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = { onLabelChange(labelText); onDismiss() },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF8B5CF6)),
                ) {
                    Text("Save")
                }
            }
        }
    }
}
