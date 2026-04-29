package com.neurocomputer.neuromobile.ui.shell

import com.neurocomputer.neuromobile.data.persistence.OsPersistencePort
import com.neurocomputer.neuromobile.data.persistence.PersistedIconsState
import com.neurocomputer.neuromobile.data.persistence.PersistedOsState

internal class NoOpOsPersistence : OsPersistencePort {
    override suspend fun saveOsState(ws: String, proj: String, state: PersistedOsState) {}
    override suspend fun loadOsState(ws: String, proj: String): PersistedOsState? = null
    override suspend fun saveIconsState(ws: String, proj: String, state: PersistedIconsState) {}
    override suspend fun loadIconsState(ws: String, proj: String): PersistedIconsState? = null
}

internal fun testOsViewModel() = OsViewModel(NoOpOsPersistence())
