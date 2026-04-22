package com.neurocomputer.neuromobile.domain.model

enum class AgentType {
    NEURO,
    OPENCLAW,
    OPENCODE,
    NEUROUPWORK
}

data class AgentInfo(
    val type: AgentType,
    val name: String,
    val description: String
) {
    companion object {
        val AGENTS = listOf(
            AgentInfo(AgentType.NEURO, "Neuro", "Default AI assistant"),
            AgentInfo(AgentType.OPENCLAW, "OpenClaw", "Automation agent"),
            AgentInfo(AgentType.OPENCODE, "OpenCode", "Code editing agent"),
            AgentInfo(AgentType.NEUROUPWORK, "NeuroUpwork", "Upwork job search and automation")
        )
    }
}
