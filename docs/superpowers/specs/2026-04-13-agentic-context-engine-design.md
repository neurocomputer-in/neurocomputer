# Agentic Context Engine + Smart Prompts

**Date:** 2026-04-13
**Status:** Approved
**Goal:** Make Neuro's agentic model dramatically better at routing, planning, executing, and replying by curating optimal context per LLM call and rewriting all prompts.

## Problem

Four pain points:
1. Replies are dumb/generic — model gets raw history dump, no personality, no context awareness
2. Skills never work right — planner makes bad plans, execution fails silently
3. No memory / loses context — every message treated equally, no summarization, no prioritization
4. Can't see what it's doing — routing/planning decisions invisible to user

## Root Cause

The system sends the same raw conversation history to every LLM call regardless of purpose. A router deciding "reply or skill?" gets the same 50-message dump as a reply neuro crafting a response. This wastes tokens, dilutes attention, and produces generic results.

Research on Claude Code, Codex, and Anthropic's engineering docs confirms: **context engineering > prompt engineering**. The best agents curate optimal token sets per call.

## Solution: Context Assembler + Rewritten Prompts

### 1. Context Assembler (`core/context.py`)

New module that builds purpose-specific context for each LLM call type.

#### Context Profiles

| Profile | Used By | History Strategy | Extra Context | Target Tokens |
|---------|---------|-----------------|---------------|---------------|
| `router` | smart_router | Last 5 messages, compact | Skills list (names + 1-line desc) | ~2K |
| `planner` | planner, code_planner | Last 10 messages + summary | Full skill catalogue, env state, project info | ~6K |
| `executor` | individual neuros during DAG execution | Relevant messages only | Previous node outputs, file contents | ~4K |
| `reply` | reply, code_reply | Last 20 messages verbatim + older summary | Personality anchor, project context | ~8K |

#### History Management

- **Messages 1-20:** Kept verbatim in order
- **Messages 21+:** Auto-summarized into a 2-3 sentence block via LLM
- **Summary cached** on the `Conversation` object as `__history_summary`
- **Summary invalidated** when new messages push past the 20-message threshold
- **Format:** `"Earlier in this conversation: {summary}"`

#### Functions

```python
def build_router_context(conv, skills_list) -> dict:
    """Returns {history: str, skills: str} optimized for routing decisions."""

def build_planner_context(conv, skills_catalogue, env_state) -> dict:
    """Returns {history: str, skills: str, env_context: str, project_info: str}."""

def build_reply_context(conv, personality, project_name) -> dict:
    """Returns {history: str, personality: str, project_context: str}."""

def summarize_history(messages, llm) -> str:
    """LLM-summarize older messages into 2-3 sentences."""

def format_messages_compact(messages, limit=5) -> str:
    """Format messages as 'role: text' with truncation."""

def format_messages_full(messages, limit=20) -> str:
    """Format messages with full text, timestamps."""
```

### 2. Smart Router Prompt Rewrite

Current prompt: 80 lines of rules, examples, JSON format instructions.
New prompt: Clear role, tool-based routing, one-line rationale.

```
You are Neuro, an intelligent AI assistant. Your job is to analyze
each user message and route it to the right handler.

You MUST call exactly one tool for every message.

## When to use `reply_directly`:
- Greetings, thanks, goodbyes
- Knowledge questions ("what is X", "explain Y")
- Opinions, advice, math, conversation
- Follow-ups to prior messages
- Anything answerable from general knowledge
- DEFAULT when uncertain

## When to use `invoke_skill`:
- Explicit action requests ("lock my PC", "create a file")
- Code generation ("write a function", "build an app")
- File/project operations ("read file X", "list files")
- System commands ("take screenshot", "open explorer")

## Rules:
1. Reply directly unless the user clearly wants an ACTION performed
2. Be concise: 1-3 sentences for replies
3. No filler: skip "Sure!", "Great question!", "I'd be happy to"
4. Reference conversation context naturally
5. Include a one-line rationale in your tool call

Available skills:
{skills}

Recent conversation:
{history}
```

### 3. Planner Prompt Rewrite

```
You are Neuro's task planner. Given a user request, create a
step-by-step execution plan using available skills.

You MUST call exactly one tool.

## Rules:
1. Each step = one skill invocation (atomic)
2. Only use skills from the provided catalogue
3. For large files (>150 lines), split into multiple write steps
4. Include a summary step at the end (code_reply or reply)
5. Bias toward action — pick reasonable defaults over asking
6. Maximum 1 clarifying question, then just act

Available skills:
{skills}

User request: {goal}
Environment context: {env_context}
```

### 4. Reply Prompt Rewrite

```
You are Neuro, a helpful and concise AI assistant.

## Personality:
- Direct and clear — lead with the answer
- Reference conversation context naturally
- 1-3 sentences for simple questions, longer for explanations
- No filler phrases ("Sure!", "Absolutely!", "Great question!")
- Use markdown for code blocks and formatting

## Context:
{project_context}

Conversation:
{history}
```

### 5. Tool Descriptions as Behavior Specs

Every neuro's `conf.json` description upgraded from 1-line labels to 3-4 sentence behavior specs.

**Before:**
```json
{"description": "Create or overwrite a text file inside the active project"}
```

**After:**
```json
{"description": "Write or append content to a file in the active project. Use when the user asks to create, write, or modify files. Parameters: filepath (relative path within project), content (the file text), mode ('write' to create/overwrite, 'append' to add to existing). For generated code files exceeding 150 lines, split into multiple write calls."}
```

Key neuros to upgrade: `code_file_write`, `code_file_read`, `code_file_list`, `code_project_manager`, `code_planner`, `neuro_list`, `reply`, `code_reply`, `openclaw_delegate`.

### 6. Execution Visibility

Brain publishes structured events at each decision point:

- **Router decision:** `{"stage": "router", "action": "reply|skill", "rationale": "..."}`
- **Plan created:** `{"stage": "plan", "steps": [{"neuro": "...", "desc": "..."}]}`
- **Node progress:** Already handled by executor (node.start, node.done, thinking)

Frontend already consumes these via LiveKitProvider → chatSlice → ThinkingIndicator.

### 7. Brain Integration

`brain.py` changes:
- Use `build_router_context()` instead of raw history for smart_router calls
- Use `build_planner_context()` for planner calls
- Pass context profile in `shared_state` so neuros use the right context builder
- Publish router rationale as debug event

## Files Modified

**New:**
- `core/context.py` — context assembler module

**Prompt rewrites:**
- `neuros/smart_router/prompt.txt`
- `neuros/planner/prompt.txt`
- `neuros/code_planner/prompt.txt`
- `neuros/reply/prompt.txt`
- `neuros/code_reply/prompt.txt`

**Code changes:**
- `neuros/smart_router/code.py` — use build_router_context
- `neuros/planner/code.py` — use build_planner_context
- `neuros/code_planner/code.py` — use build_planner_context
- `neuros/reply/code.py` — use build_reply_context
- `neuros/code_reply/code.py` — use build_reply_context
- `core/brain.py` — integrate context assembler, publish rationale
- `core/conversation.py` — add summary caching (history_summary field)

**Description upgrades:**
- ~10 neuro `conf.json` files — expand descriptions to 3-4 sentences

## Verification

1. Send "hi" → router replies directly with concise greeting (no skill invocation)
2. Send "what are your skills" → router replies directly with skill summary
3. Send "write a python hello world" → router invokes skill → planner creates plan → executor runs → reply summarizes
4. Multi-turn conversation → reply references prior context naturally
5. 30+ message conversation → history summarization kicks in, context stays manageable
6. Check token counts: router calls < 3K, planner calls < 8K, reply calls < 10K

## Risks

| Risk | Mitigation |
|------|------------|
| Summarization quality | Use the same LLM model; summary is 2-3 sentences, hard to get wrong |
| Context assembler adds latency | Summarization cached; profile building is string formatting, <1ms |
| New prompts change routing behavior | Test with 10+ common messages before deploying |
| Token budget estimation wrong | Log actual token counts per call type, adjust thresholds |
