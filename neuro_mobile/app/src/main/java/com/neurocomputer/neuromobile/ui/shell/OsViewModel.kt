package com.neurocomputer.neuromobile.ui.shell

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.model.*
import com.neurocomputer.neuromobile.data.persistence.OsPersistencePort
import com.neurocomputer.neuromobile.data.persistence.PersistedIconsState
import com.neurocomputer.neuromobile.data.persistence.PersistedOsState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OsState(
    val windows: List<WindowState> = emptyList(),
    val activeWindowId: String? = null,
    val nextZIndex: Int = 1,
    val closedCids: Set<String> = emptySet(),
    val launcherOpen: Boolean = false,
)

@HiltViewModel
class OsViewModel @Inject constructor(
    private val persistence: OsPersistencePort,
) : ViewModel() {

    // No-arg constructor for unit tests — avoids Android DataStore dependency
    constructor() : this(NoOpOsPersistence())

    private val _state = MutableStateFlow(OsState())
    val state: StateFlow<OsState> = _state.asStateFlow()

    private var currentWs: String = "global"
    private var currentProj: String = "global"

    init {
        @OptIn(FlowPreview::class)
        viewModelScope.launch {
            _state
                .debounce(500)
                .collect { s -> persist(s) }
        }
    }

    fun setContext(ws: String, proj: String) {
        currentWs = ws; currentProj = proj
        viewModelScope.launch { restore() }
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

// Unit-test stub — implements OsPersistencePort without touching Android DataStore
private class NoOpOsPersistence : OsPersistencePort {
    override suspend fun saveOsState(ws: String, proj: String, state: PersistedOsState) {}
    override suspend fun loadOsState(ws: String, proj: String) = null
    override suspend fun saveIconsState(ws: String, proj: String, state: PersistedIconsState) {}
    override suspend fun loadIconsState(ws: String, proj: String) = null
}
