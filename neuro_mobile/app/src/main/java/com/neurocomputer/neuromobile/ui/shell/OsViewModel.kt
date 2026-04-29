package com.neurocomputer.neuromobile.ui.shell

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.model.*
import com.neurocomputer.neuromobile.data.persistence.OsPersistencePort
import com.neurocomputer.neuromobile.data.persistence.PersistedIconsState
import com.neurocomputer.neuromobile.data.persistence.PersistedOsState
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.repository.WorkspaceRepository
import com.neurocomputer.neuromobile.data.service.WebSocketService
import com.neurocomputer.neuromobile.domain.model.Project
import com.neurocomputer.neuromobile.domain.model.Workspace
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject

data class OsState(
    val windows: List<WindowState> = emptyList(),
    val activeWindowId: String? = null,
    val nextZIndex: Int = 1,
    val closedCids: Set<String> = emptySet(),
    val launcherOpen: Boolean = false,
    // Workspace / project context
    val workspaces: List<Workspace> = emptyList(),
    val currentWorkspaceId: String = "default",
    val projects: List<Project> = emptyList(),
    // null means "All Projects" (no filter); otherwise a project id.
    val currentProjectId: String? = null,
)

@HiltViewModel
class OsViewModel @Inject constructor(
    private val persistence: OsPersistencePort,
    private val workspaceRepository: WorkspaceRepository,
    private val wsService: WebSocketService,
    private val backendUrlRepository: BackendUrlRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(OsState())
    val state: StateFlow<OsState> = _state.asStateFlow()

    private val _wsConnected = MutableStateFlow(false)
    val wsConnected: StateFlow<Boolean> = _wsConnected.asStateFlow()

    private val pingClient = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.SECONDS)
        .build()

    private var currentWs: String = "default"
    private var currentProj: String = "all"

    init {
        @OptIn(FlowPreview::class)
        viewModelScope.launch {
            _state
                .drop(1)
                .debounce(500)
                .collect { s -> persist(s) }
        }
        viewModelScope.launch { loadWorkspaces() }
        viewModelScope.launch { loadProjects(currentWs) }
        viewModelScope.launch { pingLoop() }
    }

    private suspend fun pingLoop() {
        while (true) {
            val base = backendUrlRepository.currentUrl.value.trimEnd('/')
            val ok = withContext(Dispatchers.IO) {
                try {
                    val req = Request.Builder().url("$base/health").build()
                    pingClient.newCall(req).execute().use { it.isSuccessful }
                } catch (_: Exception) { false }
            }
            _wsConnected.value = ok
            delay(5_000)
        }
    }

    fun setContext(ws: String, proj: String) {
        currentWs = ws; currentProj = proj
        viewModelScope.launch { restore() }
    }

    fun selectWorkspace(workspaceId: String) {
        if (workspaceId == _state.value.currentWorkspaceId) return
        _state.update { it.copy(currentWorkspaceId = workspaceId, currentProjectId = null) }
        currentWs = workspaceId
        currentProj = "all"
        viewModelScope.launch { loadProjects(workspaceId) }
        viewModelScope.launch { restore() }
    }

    fun selectProject(projectId: String?) {
        if (projectId == _state.value.currentProjectId) return
        _state.update { it.copy(currentProjectId = projectId) }
        currentProj = projectId ?: "all"
        viewModelScope.launch { restore() }
    }

    private suspend fun loadWorkspaces() {
        val ws = workspaceRepository.listWorkspaces()
        _state.update { it.copy(workspaces = ws) }
    }

    private suspend fun loadProjects(workspaceId: String) {
        val p = workspaceRepository.listProjects(workspaceId)
        _state.update { it.copy(projects = p) }
    }

    fun openWindow(window: WindowState) {
        _state.update { s ->
            s.copy(
                windows = s.windows + window.copy(zIndex = s.nextZIndex),
                activeWindowId = window.id,
                nextZIndex = s.nextZIndex + 1,
            )
        }
    }

    fun closeWindow(windowId: String) {
        _state.update { s ->
            val remaining = s.windows.filter { it.id != windowId }
            s.copy(
                windows = remaining,
                activeWindowId = if (s.activeWindowId == windowId)
                    remaining.maxByOrNull { it.zIndex }?.id else s.activeWindowId,
            )
        }
    }

    fun focusWindow(windowId: String) {
        _state.update { s ->
            s.copy(
                windows = s.windows.map { w ->
                    if (w.id == windowId) w.copy(zIndex = s.nextZIndex) else w
                },
                activeWindowId = windowId,
                nextZIndex = s.nextZIndex + 1,
            )
        }
    }

    fun addTabToWindow(windowId: String, tab: WindowTab, makeActive: Boolean) {
        _state.update { s ->
            s.copy(windows = s.windows.map { w ->
                if (w.id != windowId) w
                else w.copy(
                    tabs = w.tabs + tab,
                    activeTabId = if (makeActive) tab.id else w.activeTabId,
                )
            })
        }
    }

    fun closeTab(windowId: String, tabId: String) {
        val win = _state.value.windows.find { it.id == windowId } ?: return
        if (win.tabs.size == 1) { closeWindow(windowId); return }
        _state.update { s ->
            s.copy(windows = s.windows.map { w ->
                if (w.id != windowId) w
                else {
                    val remaining = w.tabs.filter { it.id != tabId }
                    w.copy(
                        tabs = remaining,
                        activeTabId = if (w.activeTabId == tabId) {
                            val closedIndex = w.tabs.indexOfFirst { it.id == tabId }
                            remaining[minOf(closedIndex, remaining.lastIndex)].id
                        } else w.activeTabId,
                    )
                }
            })
        }
    }

    fun setActiveTab(windowId: String, tabId: String) {
        _state.update { s ->
            s.copy(windows = s.windows.map { w ->
                if (w.id != windowId) w else w.copy(activeTabId = tabId)
            })
        }
    }

    fun reorderTabs(windowId: String, from: Int, to: Int) {
        _state.update { s ->
            s.copy(windows = s.windows.map { w ->
                if (w.id != windowId) w
                else {
                    val tabs = w.tabs.toMutableList()
                    tabs.add(to, tabs.removeAt(from))
                    w.copy(tabs = tabs)
                }
            })
        }
    }

    fun goHome() { _state.update { it.copy(activeWindowId = null) } }

    fun restoreWindows(windows: List<WindowState>, activeWindowId: String?) {
        _state.update { it.copy(windows = windows, activeWindowId = activeWindowId) }
    }

    private suspend fun restore() {
        val saved = persistence.loadOsState(currentWs, currentProj) ?: return
        restoreWindows(saved.windows, saved.activeWindowId)
    }

    private suspend fun persist(s: OsState) {
        persistence.saveOsState(
            currentWs, currentProj,
            PersistedOsState(windows = s.windows, activeWindowId = s.activeWindowId)
        )
    }
}
