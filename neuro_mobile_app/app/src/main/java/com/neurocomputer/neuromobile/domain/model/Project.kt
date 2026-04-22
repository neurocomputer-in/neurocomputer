package com.neurocomputer.neuromobile.domain.model

data class ProjectSession(
    val openTabs: List<String> = emptyList(),
    val activeTab: String? = null
)

data class Project(
    val id: String?,           // null = NoProject
    val name: String,
    val description: String = "",
    val color: String = "#8B5CF6",
    val updatedAt: String = "",
    val conversationCount: Int = 0,
    val sessionState: ProjectSession = ProjectSession(),
    val agents: List<String> = listOf("neuro")
)

object NoProject {
    val instance = Project(
        id = null,
        name = "NoProject",
        description = "Default workspace — all unassigned conversations",
        color = "#666666",
        agents = listOf("neuro", "openclaw", "opencode", "neuroupwork")
    )
    /** Wire ID used in API calls to represent null/NoProject. */
    const val API_ID = "none"
    /** DB row ID for NoProject session persistence. */
    const val DB_ID = "__noproject__"
}

/** Convert a Project's id to the string used in API calls. */
fun Project.apiId(): String = id ?: NoProject.API_ID
