package com.neurocomputer.neuromobile.data.repository

import com.neurocomputer.neuromobile.domain.model.Project
import com.neurocomputer.neuromobile.domain.model.Workspace
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Backed by `/workspaces` and `/projects?workspace_id=X`. The mobile app needs
 * these read-only for the workspace/project switcher; create/edit can stay on
 * the web side for now.
 */
@Singleton
class WorkspaceRepository @Inject constructor(
    private val httpClient: OkHttpClient,
    private val backendUrlRepository: BackendUrlRepository,
) {
    suspend fun listWorkspaces(): List<Workspace> = withContext(Dispatchers.IO) {
        try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val resp = httpClient.newCall(
                Request.Builder().url("$baseUrl/workspaces").get().build()
            ).execute()
            resp.use {
                if (!it.isSuccessful) return@withContext emptyList<Workspace>()
                val body = it.body?.string() ?: return@withContext emptyList<Workspace>()
                JSONArray(body).toWorkspaceList()
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    suspend fun listProjects(workspaceId: String): List<Project> = withContext(Dispatchers.IO) {
        try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val resp = httpClient.newCall(
                Request.Builder().url("$baseUrl/projects?workspace_id=$workspaceId").get().build()
            ).execute()
            resp.use {
                if (!it.isSuccessful) return@withContext emptyList<Project>()
                val body = it.body?.string() ?: return@withContext emptyList<Project>()
                JSONArray(body).toProjectList()
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun JSONArray.toWorkspaceList(): List<Workspace> {
        return (0 until length()).map { i ->
            val o = getJSONObject(i)
            Workspace(
                id = o.optString("id"),
                name = o.optString("name", "Workspace"),
                description = o.optString("description", ""),
                color = o.optString("color", "#8B5CF6"),
                emoji = o.optString("emoji", "🏢"),
                agents = o.optJSONArray("agents")?.let { arr ->
                    (0 until arr.length()).map { arr.getString(it) }
                } ?: listOf("neuro"),
            )
        }
    }

    private fun JSONArray.toProjectList(): List<Project> {
        return (0 until length()).map { i ->
            val o = getJSONObject(i)
            Project(
                id = o.optString("id").ifEmpty { null },
                name = o.optString("name", "Project"),
                description = o.optString("description", ""),
                color = o.optString("color", "#8B5CF6"),
                conversationCount = o.optInt("conversationCount", 0),
                agents = o.optJSONArray("agents")?.let { arr ->
                    (0 until arr.length()).map { arr.getString(it) }
                } ?: listOf("neuro"),
            )
        }
    }
}
