package com.neurocomputer.neuromobile.data.persistence

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

val Context.osDataStore by preferencesDataStore(name = "neuro_os")

@Singleton
open class OsPersistence @Inject constructor(@ApplicationContext private val context: Context) {

    private fun osKey(ws: String, proj: String) =
        stringPreferencesKey("neuro_os_${ws}_${proj}")

    private fun iconsKey(ws: String, proj: String) =
        stringPreferencesKey("neuro_icons_${ws}_${proj}")

    open suspend fun saveOsState(ws: String, proj: String, state: PersistedOsState) {
        context.osDataStore.edit { it[osKey(ws, proj)] = state.toJson() }
    }

    open suspend fun loadOsState(ws: String, proj: String): PersistedOsState? = runCatching {
        context.osDataStore.data.first()[osKey(ws, proj)]?.toPersistedOsState()
    }.onFailure { e ->
        android.util.Log.w("OsPersistence", "loadOsState failed ws=$ws proj=$proj", e)
    }.getOrNull()

    open suspend fun saveIconsState(ws: String, proj: String, state: PersistedIconsState) {
        context.osDataStore.edit { it[iconsKey(ws, proj)] = state.toJson() }
    }

    open suspend fun loadIconsState(ws: String, proj: String): PersistedIconsState? = runCatching {
        context.osDataStore.data.first()[iconsKey(ws, proj)]?.toPersistedIconsState()
    }.onFailure { e ->
        android.util.Log.w("OsPersistence", "loadIconsState failed ws=$ws proj=$proj", e)
    }.getOrNull()
}
