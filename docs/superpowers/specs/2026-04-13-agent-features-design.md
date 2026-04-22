# Agent Features Design

## Overview

Five features to make agent selection functional: filtering sessions by agent, agent icons in TabBar, agent change on empty conversations, and agency-agent management.

## 1. Agent Dropdown = Filter Only

**Problem**: AgentDropdown currently calls `setSelectedAgent()` which changes the global selected agent, affecting the active conversation's display. It should only filter visibility.

**Solution**: 
- AgentDropdown updates `agentFilter` (already exists in agentSlice), not `selectedAgent`
- `selectedAgent` is only set when creating a new conversation — derived from current `agentFilter` at creation time
- Add "All Agents" option to dropdown (maps to `AgentType.ALL`)

**Files**: `AgentDropdown.tsx`, `agentSlice.ts`, `page.tsx`

## 2. Filter Open Sessions in Sidebar + TabBar

Both Sidebar and TabBar filter `openTabs` before rendering:
```
agentFilter === 'all' ? openTabs : openTabs.filter(t => t.agentId === agentFilter)
```

- Sidebar "Open Sessions" — filtered by agent
- TabBar (bottom) — filtered by agent  
- "All Agents" → no filter, show everything
- If active tab gets filtered out → set activeTabCid to first visible tab or null

**Files**: `Sidebar.tsx`, `TabBar.tsx`

## 3. Agent Icons in TabBar

Each tab in the bottom TabBar shows a small AgentIcon (14px) before the title. Derived from `tab.agentId` via `AGENT_LIST` lookup. Uses existing `AgentIcon` component.

**Files**: `TabBar.tsx`

## 4. Change Agent on Empty Conversation

If `tabMessages[cid]` is empty or undefined, show an agent selector near the chat input or in the empty chat state. When changed:
- Update `tab.agentId` in Redux via new `updateTabAgent` reducer
- Call backend PATCH `/conversation/{cid}` with `{ agent_id: newAgentId }`

Need new API: `apiUpdateConversationAgent(cid, agentId)` and backend endpoint support.

**Files**: `conversationSlice.ts`, `ChatPanel.tsx` or `ChatInput.tsx`, `api.ts`, `server.py`

## 5. Agency-Agent Management

Add edit capability to AgencyDropdown — gear icon per agency that opens a popover/modal. Shows all AGENT_LIST items with toggle checkboxes. Changes call `PATCH /agencies/{id}` with `{ agents: [...] }`.

Backend already supports: `PATCH /agencies/{agency_id}` with agents field → `db.update_agency()`.

Need new API function: `apiUpdateAgency(id, data)`.

**Files**: `AgencyDropdown.tsx` (or new `AgencyAgentEditor.tsx`), `api.ts`

## Data Flow

```
AgentDropdown selection → agentFilter state
                        ↓
Sidebar/TabBar read agentFilter → filter openTabs for display
                        ↓
"+" button → createConversation(agentId = current agentFilter or selectedAgent)
                        ↓
New tab inherits agentId → visible when that agent is filtered
```

## Non-Goals

- No agent-scoped tab persistence (tabs stay in memory, just filtered)
- No changes to conversation message format
- No changes to backend conversation storage structure
