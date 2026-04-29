package com.neurocomputer.neuromobile.ui.shell

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.APP_LIST
import com.neurocomputer.neuromobile.data.model.AppId
import com.neurocomputer.neuromobile.data.persistence.OsPersistencePort
import com.neurocomputer.neuromobile.data.persistence.PersistedIconsState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class IconsState(
    val mobileOrder: List<AppId> = APP_LIST.map { it.id },
    val dockPins: List<AppId> = APP_LIST.filter { it.pinned }.map { it.id },
)

@HiltViewModel
class IconsViewModel @Inject constructor(
    private val persistence: OsPersistencePort,
) : ViewModel() {

    private val _state = MutableStateFlow(IconsState())
    val state: StateFlow<IconsState> = _state.asStateFlow()

    private var currentWs = "global"
    private var currentProj = "global"

    init {
        @OptIn(FlowPreview::class)
        viewModelScope.launch {
            _state.debounce(500).collect { persist(it) }
        }
    }

    fun setContext(ws: String, proj: String) {
        currentWs = ws; currentProj = proj
        viewModelScope.launch { restore() }
    }

    fun reorderIcons(from: Int, to: Int) {
        _state.update { s ->
            val list = s.mobileOrder.toMutableList()
            list.add(to, list.removeAt(from))
            s.copy(mobileOrder = list)
        }
    }

    private suspend fun restore() {
        val saved = persistence.loadIconsState(currentWs, currentProj) ?: return
        _state.update {
            it.copy(
                mobileOrder = saved.mobileOrder.mapNotNull { name ->
                    runCatching { AppId.valueOf(name) }.getOrNull()
                },
                dockPins = saved.dockPins.mapNotNull { name ->
                    runCatching { AppId.valueOf(name) }.getOrNull()
                },
            )
        }
    }

    private suspend fun persist(s: IconsState) {
        persistence.saveIconsState(
            currentWs, currentProj,
            PersistedIconsState(
                mobileOrder = s.mobileOrder.map { it.name },
                dockPins = s.dockPins.map { it.name },
            )
        )
    }
}
