package com.neurocomputer.neuromobile.ui.apps.ide

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput

@Composable
fun GraphCanvas(
    nodes: List<IdeNode>,
    edges: List<IdeEdge>,
    selectedNodeId: String?,
    zoom: Float,
    panOffset: Offset,
    onZoomChange: (Float) -> Unit,
    onPanChange: (Offset) -> Unit,
    onNodeTap: (String?) -> Unit,
    onNodeDrag: (id: String, dx: Float, dy: Float) -> Unit,
    modifier: Modifier = Modifier,
) {
    var draggingNodeId by remember { mutableStateOf<String?>(null) }

    // C1: capture latest nodes without restarting gesture coroutines
    val currentNodes by rememberUpdatedState(nodes)

    // Node size constants
    val nodeW = 120f
    val nodeH = 48f

    // Convert screen coords to canvas coords
    fun toCanvas(screen: Offset) = Offset(
        (screen.x - panOffset.x) / zoom,
        (screen.y - panOffset.y) / zoom,
    )

    // C1: use currentNodes so nodeAt() always sees current positions
    fun nodeAt(screen: Offset): IdeNode? {
        val c = toCanvas(screen)
        return currentNodes.lastOrNull { n ->
            c.x >= n.x && c.x <= n.x + nodeW && c.y >= n.y && c.y <= n.y + nodeH
        }
    }

    // C2: hoist Paint outside Canvas draw lambda to avoid per-frame allocation
    val textPaint = remember {
        android.graphics.Paint().apply {
            color = android.graphics.Color.WHITE
            isAntiAlias = true
            textAlign = android.graphics.Paint.Align.CENTER
        }
    }

    Canvas(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0a0a12))
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, gestureZoom, _ ->
                    onZoomChange((zoom * gestureZoom).coerceIn(0.2f, 5f))
                    onPanChange(panOffset + pan)
                }
            }
            // C1: key = Unit so drag gesture coroutine never restarts mid-drag
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { pos -> draggingNodeId = nodeAt(pos)?.id },
                    onDrag = { change, drag ->
                        change.consume()
                        draggingNodeId?.let { id ->
                            onNodeDrag(id, drag.x / zoom, drag.y / zoom)
                        }
                        if (draggingNodeId == null) onPanChange(panOffset + drag)
                    },
                    onDragEnd = {
                        draggingNodeId = null
                    },
                )
            }
            // C1: key = Unit so tap gesture coroutine never restarts mid-gesture
            .pointerInput(Unit) {
                detectTapGestures { pos ->
                    // I3: pass nullable id directly — null means "no node"
                    onNodeTap(nodeAt(pos)?.id)
                }
            }
    ) {
        // Draw edges first (behind nodes)
        val nodeMap = nodes.associateBy { it.id }
        edges.forEach { edge ->
            val from = nodeMap[edge.fromId] ?: return@forEach
            val to = nodeMap[edge.toId] ?: return@forEach
            drawBezierEdge(from, to, nodeW, nodeH, panOffset, zoom)
        }

        // Draw nodes
        nodes.forEach { node ->
            val sx = node.x * zoom + panOffset.x
            val sy = node.y * zoom + panOffset.y
            val sw = nodeW * zoom
            val sh = nodeH * zoom
            val isSelected = node.id == selectedNodeId
            val bgColor = Color(node.color or 0xFF000000.toLong())

            drawRoundRect(
                color = if (isSelected) bgColor.copy(alpha = 1f) else bgColor.copy(alpha = 0.7f),
                topLeft = Offset(sx, sy),
                size = Size(sw, sh),
                cornerRadius = CornerRadius(8f * zoom),
            )
            if (isSelected) {
                drawRoundRect(
                    color = Color.White,
                    topLeft = Offset(sx, sy),
                    size = Size(sw, sh),
                    cornerRadius = CornerRadius(8f * zoom),
                    style = Stroke(width = 2f),
                )
            }

            // C2: update only zoom-dependent field per node; object is reused
            textPaint.textSize = 12f * zoom
            drawContext.canvas.nativeCanvas.drawText(
                node.label,
                sx + sw / 2f,
                sy + sh / 2f + (textPaint.textSize / 3f),
                textPaint,
            )
        }
    }
}

private fun DrawScope.drawBezierEdge(
    from: IdeNode, to: IdeNode,
    nodeW: Float, nodeH: Float,
    pan: Offset, zoom: Float,
) {
    val fx = (from.x + nodeW / 2) * zoom + pan.x
    val fy = (from.y + nodeH) * zoom + pan.y
    val tx = (to.x + nodeW / 2) * zoom + pan.x
    val ty = to.y * zoom + pan.y
    // I1: abs() so control points bow correctly when target is above source
    val cpDy = (kotlin.math.abs(ty - fy) / 2f).coerceAtLeast(60f * zoom)

    val path = Path().apply {
        moveTo(fx, fy)
        cubicTo(fx, fy + cpDy, tx, ty - cpDy, tx, ty)
    }
    drawPath(
        path = path,
        color = Color(0xFF6B7280),
        style = Stroke(width = 1.5f, cap = StrokeCap.Round),
    )
    drawCircle(color = Color(0xFF6B7280), radius = 4f * zoom.coerceAtLeast(0.5f), center = Offset(tx, ty))
}
