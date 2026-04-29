package com.neurocomputer.neuromobile.ui.apps.ide

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

data class IdeNode(
    val id: String,
    val label: String,
    val x: Float,   // canvas units, will be scaled by zoom
    val y: Float,
    val color: Long = 0xFF8B5CF6,
)

data class IdeEdge(
    val fromId: String,
    val toId: String,
)

data class IdeState(
    val nodes: List<IdeNode> = emptyList(),
    val edges: List<IdeEdge> = emptyList(),
    val selectedNodeId: String? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    // pan/zoom — managed in GraphCanvas composable state, not in VM
)

@HiltViewModel(assistedFactory = IDEViewModel.Factory::class)
class IDEViewModel @AssistedInject constructor(
    @Assisted val cid: String,
    private val backendUrlRepository: BackendUrlRepository,
    private val httpClient: OkHttpClient,
) : ViewModel() {

    @AssistedFactory
    interface Factory {
        fun create(cid: String): IDEViewModel
    }

    private val _state = MutableStateFlow(IdeState())
    val state: StateFlow<IdeState> = _state.asStateFlow()

    init {
        loadGraph()
    }

    private fun loadGraph() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/neuroide/graph").build())
                        .execute()
                        .use { r -> r.body?.string() ?: "[]" }
                }
                val json = JSONObject(body)
                val nodesArr = json.optJSONArray("nodes")
                val edgesArr = json.optJSONArray("edges")

                val nodes = mutableListOf<IdeNode>()
                if (nodesArr != null) {
                    for (i in 0 until nodesArr.length()) {
                        val n = nodesArr.getJSONObject(i)
                        nodes += IdeNode(
                            id = n.getString("id"),
                            label = n.optString("label", n.getString("id")),
                            x = n.optDouble("x", (i % 4) * 200.0 + 50.0).toFloat(),
                            y = n.optDouble("y", (i / 4) * 150.0 + 50.0).toFloat(),
                            color = n.optLong("color", 0xFF8B5CF6),
                        )
                    }
                }

                val edges = mutableListOf<IdeEdge>()
                if (edgesArr != null) {
                    for (i in 0 until edgesArr.length()) {
                        val e = edgesArr.getJSONObject(i)
                        edges += IdeEdge(
                            fromId = e.getString("from"),
                            toId = e.getString("to"),
                        )
                    }
                }

                _state.update { it.copy(nodes = nodes, edges = edges) }
            } catch (e: Exception) {
                _state.update { it.copy(errorMessage = e.message) }
            } finally {
                _state.update { it.copy(isLoading = false) }
            }
        }
    }

    fun selectNode(id: String?) = _state.update { it.copy(selectedNodeId = id) }

    fun moveNode(id: String, dx: Float, dy: Float) {
        _state.update { s ->
            s.copy(nodes = s.nodes.map { n ->
                if (n.id == id) n.copy(x = n.x + dx, y = n.y + dy) else n
            })
        }
    }

    fun addNode() {
        val id = "node-${System.currentTimeMillis()}"
        val newNode = IdeNode(id = id, label = "New Node", x = 100f, y = 100f)
        _state.update { it.copy(nodes = it.nodes + newNode, selectedNodeId = id) }
    }

    fun updateNodeLabel(id: String, label: String) {
        _state.update { s ->
            s.copy(nodes = s.nodes.map { n -> if (n.id == id) n.copy(label = label) else n })
        }
    }

    fun refresh() = loadGraph()
}
