# Session Management & Agent-per-Project Redesign

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix session persistence for NoProject, filter conversations by selected agent, add "All Agents" option, and implement per-project agent onboarding.

**Architecture:** NoProject gets a real DB row (id="__noproject__") so session_state persists like any other project. The Project model gains an `agents` list (default `["neuro"]` for real projects, all agents for NoProject). Conversations are filtered by both project AND selected agent. A new "All" option in the agent dropdown shows all conversations unfiltered.

**Tech Stack:** Kotlin/Jetpack Compose (Android), Python/FastAPI (server), SQLite (aiosqlite)

---

## File Structure

**Server (Python):**
- Modify: `server.py` — GET /projects endpoint, NoProject session handling
- Modify: `core/db.py` — Ensure NoProject row in DB, add `agents` column to projects table

**Mobile (Kotlin):**
- Modify: `neuro_mobile_app/.../domain/model/Project.kt` — Add `agents` field, update NoProject
- Modify: `neuro_mobile_app/.../domain/model/Agent.kt` — Add ALL_AGENTS sentinel
- Modify: `neuro_mobile_app/.../data/repository/ProjectRepository.kt` — Fix saveSession for NoProject, parse agents field
- Modify: `neuro_mobile_app/.../ui/screens/ConversationScreen.kt` — Agent-filtered conversations, restoreSession fixes
- Modify: `neuro_mobile_app/.../ui/components/AgentDropdown.kt` — Add "All Agents" option, filter by project agents

---

### Task 1: Fix NoProject Session Persistence (Server)

**Files:**
- Modify: `core/db.py` — Ensure NoProject row exists, lines 45-65 (init), lines 226-240 (create)
- Modify: `server.py` — GET /projects reads NoProject from DB, lines 756-786

- [ ] **Step 1: Add NoProject row auto-creation in db.py**

In `core/db.py`, inside the `_init_db` method (after the CREATE TABLE for projects), add an upsert for the NoProject row:

```python
                # Ensure NoProject row exists
                await db.execute("""
                    INSERT OR IGNORE INTO projects (id, name, description, color, created_at, updated_at)
                    VALUES ('__noproject__', 'NoProject', 'Default workspace', '#666666', ?, ?)
                """, (now, now))
```

Place this right after the `CREATE TABLE IF NOT EXISTS projects` block. You'll need to add `now = datetime.utcnow().isoformat()` before it (check if it already exists in context). Note: Task 3 will update this INSERT to also include the `agents` column.

- [ ] **Step 2: Update server.py GET /projects to read NoProject from DB**

In `server.py`, replace the hardcoded `no_project` dict in `list_projects()` (lines 776-785) with a DB read:

```python
    # Read NoProject from DB (has real session_state)
    no_project_row = await db.get_project("__noproject__")
    if no_project_row:
        no_project = no_project_row
        no_project["id"] = None  # Wire format: null id for NoProject
        no_project["conversationCount"] = no_project_count
    else:
        no_project = {
            "id": None,
            "name": "NoProject",
            "description": "Default workspace",
            "color": "#666666",
            "sessionState": {"openTabs": [], "activeTab": None},
            "conversationCount": no_project_count,
            "createdAt": "",
            "updatedAt": "",
        }
    return [no_project] + projects
```

- [ ] **Step 3: Update PATCH /projects to handle NoProject ID**

In `server.py`, the `update_project` endpoint receives `pid` from the URL. When the mobile sends `"__noproject__"`, it should work. Check that `db.update_project("__noproject__", ...)` updates the correct row. No code change needed if the DB row exists — just verify.

- [ ] **Step 4: Verify get_project handles __noproject__**

Read `core/db.py` `get_project()` method. It should work for any string ID. Verify by checking the function. If it returns `sessionState` correctly (parses `session_state` JSON column), no change needed.

- [ ] **Step 5: Commit**

```bash
git add core/db.py server.py
git commit -m "fix: persist NoProject session state in DB instead of hardcoding empty"
```

---

### Task 2: Fix NoProject Session Persistence (Mobile)

**Files:**
- Modify: `neuro_mobile_app/.../domain/model/Project.kt` — Update NoProject.API_ID
- Modify: `neuro_mobile_app/.../data/repository/ProjectRepository.kt` — Fix saveSession, lines 91-92
- Modify: `neuro_mobile_app/.../ui/screens/ConversationScreen.kt` — Fix persistSession, line 733

- [ ] **Step 1: Add NOPROJECT_DB_ID constant to Project.kt**

In `Project.kt`, update the `NoProject` object:

```kotlin
object NoProject {
    val instance = Project(
        id = null,
        name = "NoProject",
        description = "Default workspace — all unassigned conversations",
        color = "#666666"
    )
    /** Wire ID used in API calls to represent null/NoProject. */
    const val API_ID = "none"
    /** DB row ID for NoProject session persistence. */
    const val DB_ID = "__noproject__"
}
```

- [ ] **Step 2: Fix ProjectRepository.saveSession to handle NoProject**

In `ProjectRepository.kt`, replace line 92:

```kotlin
    suspend fun saveSession(projectId: String?, session: ProjectSession) = withContext(Dispatchers.IO) {
        val pid = projectId ?: NoProject.DB_ID  // Use DB_ID instead of bailing out
        val sessionJson = JSONObject().apply {
            put("openTabs", org.json.JSONArray(session.openTabs))
            put("activeTab", session.activeTab)
        }
        val payload = JSONObject().apply {
            put("sessionState", sessionJson)
        }.toString().toRequestBody(json)
        try {
            val req = Request.Builder()
                .url("${baseUrl()}/projects/$pid")
                .neuroHeaders()
                .patch(payload)
                .build()
            client.newCall(req).execute()
        } catch (_: Exception) {}
    }
```

- [ ] **Step 3: Fix ConversationScreen.persistSession to handle NoProject**

In `ConversationScreen.kt`, replace line 733:

```kotlin
    private fun persistSession() {
        val pid = _selectedProject.value.id
            ?: com.neurocomputer.neuromobile.domain.model.NoProject.DB_ID
        val session = com.neurocomputer.neuromobile.domain.model.ProjectSession(
            openTabs = _openTabs.value.map { it.cid },
            activeTab = _activeTabCid.value
        )
        viewModelScope.launch {
            try { projectRepository.saveSession(pid, session) } catch (_: Exception) {}
        }
    }
```

- [ ] **Step 4: Commit**

```bash
git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/model/Project.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/data/repository/ProjectRepository.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/screens/ConversationScreen.kt
git commit -m "fix: enable session persistence for NoProject using DB row"
```

---

### Task 3: Add `agents` Column to Projects (Server)

**Files:**
- Modify: `core/db.py` — Add agents column, update create/list/get/update methods
- Modify: `server.py` — Pass agents in project responses, add endpoint to manage agents

- [ ] **Step 1: Add agents column to projects table in db.py**

In `core/db.py`, inside `_init_db`, after the CREATE TABLE for projects, add a migration:

```python
                # Migration: add agents column if missing
                try:
                    await db.execute("ALTER TABLE projects ADD COLUMN agents TEXT DEFAULT '[]'")
                except Exception:
                    pass  # Column already exists
```

Also update the NoProject upsert (from Task 1) to include agents with all types:

```python
                # Ensure NoProject row exists with all agents
                await db.execute("""
                    INSERT OR IGNORE INTO projects (id, name, description, color, agents, created_at, updated_at)
                    VALUES ('__noproject__', 'NoProject', 'Default workspace', '#666666', '["neuro","openclaw","opencode","neuroupwork"]', ?, ?)
                """, (now, now))
```

- [ ] **Step 2: Update list_projects to return agents**

In `core/db.py` `list_projects()`, add agents parsing (around line 260):

```python
            try:
                agents_list = json.loads(d.get("agents") or "[]")
            except Exception:
                agents_list = []
            projects.append({
                "id": d["id"],
                "name": d["name"],
                "description": d.get("description", ""),
                "color": d.get("color", "#8B5CF6"),
                "sessionState": {"openTabs": session.get("openTabs", []),
                                 "activeTab": session.get("activeTab")},
                "agents": agents_list,
                "createdAt": d.get("created_at", ""),
                "updatedAt": d.get("updated_at", ""),
            })
```

- [ ] **Step 3: Update get_project to return agents**

In `core/db.py` `get_project()`, add the same `agents` parsing. Find where it builds the return dict and add:

```python
            try:
                agents_list = json.loads(d.get("agents") or "[]")
            except Exception:
                agents_list = []
            # Include in the return dict:
            "agents": agents_list,
```

- [ ] **Step 4: Update create_project to accept and store agents**

In `core/db.py` `create_project()`, add an `agents` parameter defaulting to `["neuro"]`:

```python
    async def create_project(self, name: str, description: str = "", color: str = "#8B5CF6", agents: list = None) -> Dict[str, Any]:
        if agents is None:
            agents = ["neuro"]
        project_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO projects (id, name, description, color, agents, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (project_id, name, description, color, json.dumps(agents), now, now)
                )
                await db.commit()
        return {"id": project_id, "name": name, "description": description,
                "color": color, "agents": agents,
                "sessionState": {"openTabs": [], "activeTab": None},
                "createdAt": now, "updatedAt": now}
```

- [ ] **Step 5: Update update_project to handle agents field**

In `core/db.py` `update_project()`, add agents handling alongside existing fields:

```python
        if "agents" in fields:
            set_clauses.append("agents = ?")
            values.append(json.dumps(fields["agents"]))
```

- [ ] **Step 6: Update server.py endpoints to handle agents**

In `server.py`, update `create_project` to pass agents:

```python
@app.post("/projects")
async def create_project(body: dict):
    name = body.get("name", "New Project")
    description = body.get("description", "")
    color = body.get("color", "#8B5CF6")
    agents = body.get("agents", ["neuro"])
    project = await db.create_project(name=name, description=description, color=color, agents=agents)
    project["conversationCount"] = 0
    return project
```

Update `update_project` to handle agents:

```python
@app.patch("/projects/{pid}")
async def update_project(pid: str, body: dict):
    fields = {}
    if "name" in body:
        fields["name"] = body["name"]
    if "description" in body:
        fields["description"] = body["description"]
    if "color" in body:
        fields["color"] = body["color"]
    if "sessionState" in body:
        fields["session_state"] = body["sessionState"]
    if "agents" in body:
        fields["agents"] = body["agents"]
    await db.update_project(pid, **fields)
    return {"success": True}
```

Also update `list_projects` so NoProject read from DB already includes agents (handled by Task 1's DB read).

- [ ] **Step 7: Commit**

```bash
git add core/db.py server.py
git commit -m "feat: add per-project agents column with default neuro for new projects"
```

---

### Task 4: Parse `agents` Field in Mobile + Add "All Agents" Option

**Files:**
- Modify: `neuro_mobile_app/.../domain/model/Project.kt` — Add agents field
- Modify: `neuro_mobile_app/.../domain/model/Agent.kt` — Add ALL sentinel
- Modify: `neuro_mobile_app/.../data/repository/ProjectRepository.kt` — Parse agents from server
- Modify: `neuro_mobile_app/.../ui/components/AgentDropdown.kt` — Show "All" + project agents only

- [ ] **Step 1: Add agents field to Project data class**

In `Project.kt`, update the `Project` data class:

```kotlin
data class Project(
    val id: String?,
    val name: String,
    val description: String = "",
    val color: String = "#8B5CF6",
    val updatedAt: String = "",
    val conversationCount: Int = 0,
    val sessionState: ProjectSession = ProjectSession(),
    val agents: List<String> = listOf("neuro")
)
```

Update `NoProject.instance`:

```kotlin
object NoProject {
    val instance = Project(
        id = null,
        name = "NoProject",
        description = "Default workspace — all unassigned conversations",
        color = "#666666",
        agents = listOf("neuro", "openclaw", "opencode", "neuroupwork")
    )
    const val API_ID = "none"
    const val DB_ID = "__noproject__"
}
```

- [ ] **Step 2: Add ALL_AGENTS sentinel to Agent.kt**

In `Agent.kt`, add a sentinel AgentInfo for "All Agents":

```kotlin
enum class AgentType {
    ALL,         // Show all agents' conversations (sentinel)
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
        val ALL_AGENTS_SENTINEL = AgentInfo(AgentType.ALL, "All Agents", "Show all conversations")

        val AGENTS = listOf(
            AgentInfo(AgentType.NEURO, "Neuro", "Default AI assistant"),
            AgentInfo(AgentType.OPENCLAW, "OpenClaw", "Automation agent"),
            AgentInfo(AgentType.OPENCODE, "OpenCode", "Code editing agent"),
            AgentInfo(AgentType.NEUROUPWORK, "NeuroUpwork", "Upwork job search and automation")
        )
    }
}
```

- [ ] **Step 3: Parse agents in ProjectRepository.toProject()**

In `ProjectRepository.kt`, in the `toProject()` extension function, parse the agents array:

```kotlin
    private fun JSONObject.toProject(): Project {
        val sessionObj = optJSONObject("sessionState")
        val openTabs = mutableListOf<String>()
        sessionObj?.optJSONArray("openTabs")?.let { arr ->
            for (i in 0 until arr.length()) openTabs.add(arr.getString(i))
        }
        val activeTab = sessionObj?.optString("activeTab")?.takeIf { it.isNotEmpty() && it != "null" }

        val agentsList = mutableListOf<String>()
        optJSONArray("agents")?.let { arr ->
            for (i in 0 until arr.length()) agentsList.add(arr.getString(i))
        }
        if (agentsList.isEmpty()) agentsList.add("neuro")

        return Project(
            id = optString("id").takeIf { it.isNotEmpty() && it != "null" },
            name = optString("name", "Project"),
            description = optString("description", ""),
            color = optString("color", "#8B5CF6"),
            updatedAt = optString("updatedAt", ""),
            conversationCount = optInt("conversationCount", 0),
            sessionState = ProjectSession(openTabs = openTabs, activeTab = activeTab),
            agents = agentsList
        )
    }
```

- [ ] **Step 4: Update AgentDropdown to show "All" + filter by project agents**

In `AgentDropdown.kt`, update the `AgentDropdown` composable signature and rendering:

```kotlin
@Composable
fun AgentDropdown(
    agents: List<AgentInfo>,
    selectedAgent: AgentInfo,
    onSelect: (AgentInfo) -> Unit,
    onDismiss: () -> Unit,
    menuAlignment: Alignment = Alignment.TopStart,
    menuOffset: DpOffset = DpOffset(60.dp, 110.dp)
) {
    // Prepend "All Agents" sentinel
    val allOptions = listOf(AgentInfo.ALL_AGENTS_SENTINEL) + agents

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.3f))
            .clickable { onDismiss() }
    ) {
        Box(
            modifier = Modifier
                .align(menuAlignment)
                .offset(x = menuOffset.x, y = menuOffset.y)
                .widthIn(max = 200.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(NeuroColors.BackgroundMid)
                .clickable(enabled = false) { }
        ) {
            Column(
                modifier = Modifier.padding(8.dp)
            ) {
                allOptions.forEach { agent ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable { onSelect(agent) }
                            .background(
                                if (agent.type == selectedAgent.type) NeuroColors.GlassPrimary else Color.Transparent
                            )
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier.size(24.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            when (agent.type) {
                                AgentType.ALL -> Icon(
                                    Icons.Default.Star,
                                    contentDescription = "All",
                                    tint = NeuroColors.TextSecondary,
                                    modifier = Modifier.size(20.dp)
                                )
                                AgentType.NEURO -> Image(
                                    painter = painterResource(id = R.drawable.logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.OPENCLAW -> Image(
                                    painter = painterResource(id = R.drawable.openclaw_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.OPENCODE -> Image(
                                    painter = painterResource(id = R.drawable.opencode_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                                AgentType.NEUROUPWORK -> Image(
                                    painter = painterResource(id = R.drawable.upwork_logo),
                                    contentDescription = agent.name,
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit
                                )
                            }
                        }

                        Spacer(modifier = Modifier.width(10.dp))

                        Text(
                            text = agent.name,
                            color = NeuroColors.TextPrimary,
                            fontSize = 14.sp,
                            modifier = Modifier.weight(1f)
                        )

                        if (agent.type == selectedAgent.type) {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = "Selected",
                                tint = NeuroColors.Primary,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 5: Commit**

```bash
git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/model/Project.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/model/Agent.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/data/repository/ProjectRepository.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/components/AgentDropdown.kt
git commit -m "feat: add per-project agents field and All Agents option in dropdown"
```

---

### Task 5: Filter Conversations by Selected Agent

**Files:**
- Modify: `neuro_mobile_app/.../ui/screens/ConversationScreen.kt` — Filter conversations, update selectAgent, pass project agents to dropdown

- [ ] **Step 1: Add filtered conversations StateFlow**

In `ConversationScreen.kt`, after the existing `conversationsByAgent` StateFlow (around line 250), add a new derived flow that filters by the selected agent:

```kotlin
    /** Conversations filtered by the currently selected agent (or all if ALL selected). */
    val filteredConversations: StateFlow<List<ConversationSummary>> =
        combine(_conversations, selectedAgent) { convs, agent ->
            if (agent.type == AgentType.ALL) {
                convs
            } else {
                convs.filter { conv ->
                    conv.agentId?.equals(agent.type.name, ignoreCase = true) == true
                }
            }
        }.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())
```

You will need to add `import kotlinx.coroutines.flow.combine` at the top if not already present.

- [ ] **Step 2: Update selectAgent to NOT change current conversation's agent_id**

In `ConversationScreen.kt`, the `selectAgent()` function currently PATCHes the active conversation's agent_id. Remove that — selecting an agent in the dropdown is now a *filter* action, not a conversation mutation. Replace:

```kotlin
    fun selectAgent(agent: AgentInfo) {
        val agentType = agent.type.name.lowercase()
        viewModelScope.launch {
            backendUrlRepository.setSelectedAgent(agentType)
        }
        _showAgentDropdown.value = false
    }
```

- [ ] **Step 3: Pass project agents to AgentDropdown**

Find where `AgentDropdown` is called in the Composable (search for `AgentDropdown(` in ConversationScreen.kt). Update it to pass only the project's onboarded agents:

```kotlin
    // Where AgentDropdown is rendered:
    val project = selectedProject.collectAsState().value
    val projectAgents = AgentInfo.AGENTS.filter { agent ->
        project.agents.any { it.equals(agent.type.name, ignoreCase = true) }
    }

    AgentDropdown(
        agents = projectAgents,   // was: AgentInfo.AGENTS
        selectedAgent = selectedAgent,
        onSelect = { viewModel.selectAgent(it) },
        onDismiss = { viewModel.toggleAgentDropdown() }
    )
```

- [ ] **Step 4: Update history/sidebar list to use filteredConversations**

Find where `conversations` or `_conversations` is displayed in the conversation list/sidebar UI. Replace usages with `filteredConversations`. Look for `viewModel.conversations.collectAsState()` and change to `viewModel.filteredConversations.collectAsState()`.

- [ ] **Step 5: Handle "All Agents" in BackendUrlRepository**

When `AgentType.ALL` is selected, store `"all"` in BackendUrlRepository. Update `selectAgent`:

```kotlin
    fun selectAgent(agent: AgentInfo) {
        val agentType = if (agent.type == AgentType.ALL) "all" else agent.type.name.lowercase()
        viewModelScope.launch {
            backendUrlRepository.setSelectedAgent(agentType)
        }
        _showAgentDropdown.value = false
    }
```

Update the `selectedAgent` StateFlow mapping to handle "all":

```kotlin
    val selectedAgent: StateFlow<AgentInfo> = backendUrlRepository.selectedAgent.map { agentId ->
        if (agentId.equals("all", ignoreCase = true)) {
            AgentInfo.ALL_AGENTS_SENTINEL
        } else {
            AgentInfo.AGENTS.find { it.type.name.equals(agentId, ignoreCase = true) }
                ?: AgentInfo.AGENTS.first()
        }
    }.stateIn(viewModelScope, SharingStarted.Eagerly, AgentInfo.AGENTS.first())
```

- [ ] **Step 6: When "All Agents" selected and user creates new tab, use Neuro as default**

In `createNewTab()`, when `selectedAgent` is ALL, default to NEURO:

```kotlin
    fun createNewTab() {
        val agentType = selectedAgent.value.type
        val effectiveAgent = if (agentType == AgentType.ALL) AgentType.NEURO else agentType
        val tempCid = "new_${UUID.randomUUID().toString().take(8)}"
        _openTabs.value = _openTabs.value.map { it.copy(isActive = false) } +
            Tab(cid = tempCid, title = "New Chat", agentId = effectiveAgent.name.lowercase(), isActive = true)
        // ... rest unchanged, but use effectiveAgent.name.lowercase() for agentType in the POST body
```

- [ ] **Step 7: Commit**

```bash
git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/screens/ConversationScreen.kt
git commit -m "feat: filter conversations by selected agent, add All Agents support"
```

---

### Task 6: Add/Remove Agents on a Project (Server + Mobile)

**Files:**
- Modify: `server.py` — Add POST /projects/{pid}/agents and DELETE /projects/{pid}/agents/{agent} endpoints
- Modify: `neuro_mobile_app/.../data/repository/ProjectRepository.kt` — Add addAgent/removeAgent methods
- Modify: `neuro_mobile_app/.../ui/screens/ConversationScreen.kt` — Add agent management functions

- [ ] **Step 1: Add server endpoints for managing project agents**

In `server.py`, add after the existing PATCH /projects endpoint:

```python
@app.post("/projects/{pid}/agents")
async def add_agent_to_project(pid: str, body: dict):
    """Add an agent to a project's allowed agents list."""
    agent_id = body.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")
    project = await db.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agents = project.get("agents", ["neuro"])
    if agent_id not in agents:
        agents.append(agent_id)
        await db.update_project(pid, agents=agents)
    return {"success": True, "agents": agents}


@app.delete("/projects/{pid}/agents/{agent_id}")
async def remove_agent_from_project(pid: str, agent_id: str):
    """Remove an agent from a project. Cannot remove the last agent."""
    project = await db.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agents = project.get("agents", ["neuro"])
    if agent_id in agents:
        if len(agents) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last agent")
        agents.remove(agent_id)
        await db.update_project(pid, agents=agents)
    return {"success": True, "agents": agents}
```

- [ ] **Step 2: Add ProjectRepository methods for agent management**

In `ProjectRepository.kt`, add:

```kotlin
    suspend fun addAgentToProject(projectId: String, agentId: String) = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("agent_id", agentId)
        }.toString().toRequestBody(json)
        val req = Request.Builder()
            .url("${baseUrl()}/projects/$projectId/agents")
            .neuroHeaders()
            .post(body)
            .build()
        client.newCall(req).execute()
    }

    suspend fun removeAgentFromProject(projectId: String, agentId: String) = withContext(Dispatchers.IO) {
        val req = Request.Builder()
            .url("${baseUrl()}/projects/$projectId/agents/$agentId")
            .neuroHeaders()
            .delete()
            .build()
        client.newCall(req).execute()
    }
```

- [ ] **Step 3: Add ViewModel methods for agent management**

In `ConversationScreen.kt`, add functions:

```kotlin
    fun addAgentToProject(agentType: AgentType) {
        val pid = _selectedProject.value.id ?: return  // NoProject already has all agents
        viewModelScope.launch {
            try {
                projectRepository.addAgentToProject(pid, agentType.name.lowercase())
                // Refresh project to get updated agents list
                val projects = projectRepository.listProjects()
                _projects.value = projects
                _selectedProject.value = projects.find { it.id == pid } ?: _selectedProject.value
            } catch (e: Exception) {
                Log.e("ConversationVM", "Failed to add agent to project", e)
            }
        }
    }

    fun removeAgentFromProject(agentType: AgentType) {
        val pid = _selectedProject.value.id ?: return
        viewModelScope.launch {
            try {
                projectRepository.removeAgentFromProject(pid, agentType.name.lowercase())
                val projects = projectRepository.listProjects()
                _projects.value = projects
                _selectedProject.value = projects.find { it.id == pid } ?: _selectedProject.value
                // If the removed agent was selected, switch to "All"
                if (selectedAgent.value.type == agentType) {
                    selectAgent(AgentInfo.ALL_AGENTS_SENTINEL)
                }
            } catch (e: Exception) {
                Log.e("ConversationVM", "Failed to remove agent from project", e)
            }
        }
    }
```

- [ ] **Step 4: Commit**

```bash
git add server.py \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/data/repository/ProjectRepository.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/screens/ConversationScreen.kt
git commit -m "feat: add/remove agents on projects via API and ViewModel"
```

---

### Task 7: Agent Management UI in AgentDropdown

**Files:**
- Modify: `neuro_mobile_app/.../ui/components/AgentDropdown.kt` — Add "Add Agent" button for non-onboarded agents

- [ ] **Step 1: Update AgentDropdown to show add/remove for project agents**

In `AgentDropdown.kt`, update the signature to accept callbacks and the full agent list:

```kotlin
@Composable
fun AgentDropdown(
    agents: List<AgentInfo>,          // Project's onboarded agents
    selectedAgent: AgentInfo,
    onSelect: (AgentInfo) -> Unit,
    onDismiss: () -> Unit,
    onAddAgent: ((AgentType) -> Unit)? = null,     // null = no management (NoProject)
    onRemoveAgent: ((AgentType) -> Unit)? = null,
    menuAlignment: Alignment = Alignment.TopStart,
    menuOffset: DpOffset = DpOffset(60.dp, 110.dp)
) {
    val allOptions = listOf(AgentInfo.ALL_AGENTS_SENTINEL) + agents
    // Agents not yet onboarded (for "Add" section)
    val availableToAdd = if (onAddAgent != null) {
        AgentInfo.AGENTS.filter { candidate ->
            agents.none { it.type == candidate.type }
        }
    } else emptyList()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.3f))
            .clickable { onDismiss() }
    ) {
        Box(
            modifier = Modifier
                .align(menuAlignment)
                .offset(x = menuOffset.x, y = menuOffset.y)
                .widthIn(max = 220.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(NeuroColors.BackgroundMid)
                .clickable(enabled = false) { }
        ) {
            Column(
                modifier = Modifier.padding(8.dp)
            ) {
                // Onboarded agents (selectable)
                allOptions.forEach { agent ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable { onSelect(agent) }
                            .background(
                                if (agent.type == selectedAgent.type) NeuroColors.GlassPrimary else Color.Transparent
                            )
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        AgentIcon(agent, Modifier.size(24.dp))
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = agent.name,
                            color = NeuroColors.TextPrimary,
                            fontSize = 14.sp,
                            modifier = Modifier.weight(1f)
                        )
                        if (agent.type == selectedAgent.type) {
                            Icon(Icons.Default.Check, "Selected", tint = NeuroColors.Primary, modifier = Modifier.size(16.dp))
                        }
                    }
                }

                // "Add Agent" section (only for real projects)
                if (availableToAdd.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    HorizontalDivider(color = Color.White.copy(alpha = 0.1f))
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Add Agent",
                        color = NeuroColors.TextSecondary,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                    )
                    availableToAdd.forEach { agent ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .clickable { onAddAgent?.invoke(agent.type) }
                                .padding(horizontal = 12.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            AgentIcon(agent, Modifier.size(20.dp).alpha(0.5f))
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(agent.name, color = NeuroColors.TextSecondary, fontSize = 13.sp, modifier = Modifier.weight(1f))
                            Icon(Icons.Default.Add, "Add", tint = NeuroColors.TextSecondary, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }
    }
}

/** Reusable agent icon renderer. */
@Composable
private fun AgentIcon(agent: AgentInfo, modifier: Modifier = Modifier) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        when (agent.type) {
            AgentType.ALL -> Icon(Icons.Default.Star, "All", tint = NeuroColors.TextSecondary, modifier = Modifier.fillMaxSize(0.8f))
            AgentType.NEURO -> Image(painterResource(R.drawable.logo), agent.name, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            AgentType.OPENCLAW -> Image(painterResource(R.drawable.openclaw_logo), agent.name, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            AgentType.OPENCODE -> Image(painterResource(R.drawable.opencode_logo), agent.name, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            AgentType.NEUROUPWORK -> Image(painterResource(R.drawable.upwork_logo), agent.name, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
        }
    }
}
```

Add `import androidx.compose.ui.draw.alpha` and `import androidx.compose.material.icons.filled.Add` and `import androidx.compose.material3.HorizontalDivider` to the imports.

- [ ] **Step 2: Update caller to pass onAddAgent/onRemoveAgent**

In `ConversationScreen.kt`, where `AgentDropdown` is rendered, update:

```kotlin
    val project = selectedProject.collectAsState().value
    val projectAgents = AgentInfo.AGENTS.filter { agent ->
        project.agents.any { it.equals(agent.type.name, ignoreCase = true) }
    }

    AgentDropdown(
        agents = projectAgents,
        selectedAgent = selectedAgent,
        onSelect = { viewModel.selectAgent(it) },
        onDismiss = { viewModel.toggleAgentDropdown() },
        onAddAgent = if (project.id != null) { agentType -> viewModel.addAgentToProject(agentType) } else null,
        onRemoveAgent = if (project.id != null) { agentType -> viewModel.removeAgentFromProject(agentType) } else null,
    )
```

NoProject (id=null) gets no add/remove buttons — it always has all agents.

- [ ] **Step 3: Commit**

```bash
git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/components/AgentDropdown.kt \
       neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/screens/ConversationScreen.kt
git commit -m "feat: agent management UI in dropdown - add/remove agents per project"
```

---

### Task 8: Integration Verification

- [ ] **Step 1: Verify server starts without errors**

```bash
cd /home/ubuntu/neurocomputer && python3 -c "import ast; ast.parse(open('server.py').read()); ast.parse(open('core/db.py').read()); print('OK')"
```

- [ ] **Step 2: Verify NoProject DB row is created on startup**

```bash
cd /home/ubuntu/neurocomputer && python3 -c "
import asyncio
from core.db import db
async def check():
    await db.init()
    p = await db.get_project('__noproject__')
    print('NoProject row:', p)
asyncio.run(check())
"
```

Expected: NoProject row with id=`__noproject__`, agents list with all 4 types, sessionState.

- [ ] **Step 3: Verify Kotlin compiles (if build tools available)**

```bash
cd /home/ubuntu/neurocomputer/neuro_mobile_app && ./gradlew compileDebugKotlin 2>&1 | tail -20
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: session management redesign - NoProject persistence, agent filtering, per-project agents"
```
