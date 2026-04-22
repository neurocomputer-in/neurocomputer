# Agentic Context Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Neuro dramatically smarter by curating optimal context per LLM call and rewriting all prompts with production-quality instructions.

**Architecture:** New `core/context.py` module assembles purpose-specific context (router gets 5 messages, reply gets 20 + summary). All prompts rewritten with clear role, constraints, and no-fluff personality. Tool descriptions upgraded to 3-4 sentence behavior specs.

**Tech Stack:** Python 3.12, existing NeuroFactory/BaseBrain/Executor, MiniMax M2.5 via OpenRouter

---

### Task 1: Create Context Assembler (`core/context.py`)

**Files:**
- Create: `core/context.py`

- [ ] **Step 1: Create the context assembler module**

```python
"""
Context Assembler — builds purpose-specific context for each LLM call type.

Instead of dumping raw conversation history into every call, each profile
curates the optimal token set: router gets 5 compact messages, reply gets
20 full messages + a summary of older ones.
"""


def format_messages_compact(messages: list[dict], limit: int = 5) -> str:
    """Format last N messages as 'role: text' with truncation per message."""
    recent = messages[-limit:] if limit else messages
    lines = []
    for m in recent:
        text = m.get("text", "")
        if len(text) > 200:
            text = text[:200] + "..."
        lines.append(f"{m['sender']}: {text}")
    return "\n".join(lines)


def format_messages_full(messages: list[dict], limit: int = 20) -> str:
    """Format last N messages with full text."""
    recent = messages[-limit:] if limit else messages
    return "\n".join(f"{m['sender']}: {m['text']}" for m in recent)


def build_skills_compact(neuros: list[dict]) -> str:
    """One-line per skill: '- name: description'."""
    return "\n".join(f"- {n['name']}: {n['desc']}" for n in neuros)


def build_router_context(conv, neuros: list[dict]) -> dict:
    """Context for smart_router: compact recent history + skills list.

    Target: ~2K tokens. Router only needs to classify intent.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier: {summary}")
    history_parts.append(format_messages_compact(messages, limit=5))

    return {
        "history": "\n".join(history_parts),
        "skills": build_skills_compact(neuros),
    }


def build_planner_context(conv, neuros: list[dict], env_state=None) -> dict:
    """Context for planners: more history + full skill catalogue + env state.

    Target: ~6K tokens. Planner needs to understand the task deeply.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier in conversation: {summary}")
    history_parts.append(format_messages_full(messages, limit=10))

    env_ctx = ""
    if env_state:
        env_ctx = env_state.format_for_prompt()

    return {
        "history": "\n".join(history_parts),
        "skills": build_skills_compact(neuros),
        "env_context": env_ctx,
    }


def build_reply_context(conv, personality: str = "") -> dict:
    """Context for reply neuros: rich history with personality.

    Target: ~8K tokens. Reply needs full conversational context.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier in conversation: {summary}")
    history_parts.append(format_messages_full(messages, limit=20))

    return {
        "history": "\n".join(history_parts),
        "personality": personality,
    }


async def ensure_history_summary(conv, llm) -> None:
    """Summarize old messages if conversation exceeds 20 messages.

    Summary is cached on the conversation object. Only recomputed when
    message count changes past the threshold.
    """
    messages = conv.history()
    if len(messages) <= 20:
        return

    # Check if summary is still valid
    current_summary_count = getattr(conv, '_summary_msg_count', 0)
    if current_summary_count == len(messages):
        return

    # Summarize messages 0..(len-20)
    old_messages = messages[:-20]
    text = "\n".join(f"{m['sender']}: {m['text'][:150]}" for m in old_messages[-30:])

    summary = await llm.agenerate_text(
        f"Summarize this conversation excerpt in 2-3 sentences. Focus on key topics, decisions, and any unresolved questions:\n\n{text}",
        "You are a concise summarizer. Output only the summary, no preamble."
    )
    conv.set_history_summary(summary.strip())
    conv._summary_msg_count = len(messages)
```

- [ ] **Step 2: Commit**

```bash
git add core/context.py
git commit -m "feat: add context assembler for purpose-specific LLM context"
```

---

### Task 2: Add Summary Caching to Conversation

**Files:**
- Modify: `core/conversation.py`

- [ ] **Step 1: Add summary fields and methods**

Add these methods to the `Conversation` class in `core/conversation.py`, after the existing `set_llm_settings` method (line 49):

```python
    def get_history_summary(self) -> str:
        """Return cached history summary, or empty string."""
        return self._summary or ""

    def set_history_summary(self, summary: str) -> None:
        """Cache a history summary. Persisted to disk."""
        self._summary = summary
        self._save()
```

Add `self._summary` initialization in `__init__`, after `self.llm_settings = {}` (line 20):

```python
        self._summary = ""
```

And in the dict-format loading branch (line 30), add:

```python
            self._summary = data.get("history_summary", "") if data else ""
```

Update `_save` to include the summary — in the `data` dict (line 76-79):

```python
    def _save(self):
        data = {
            "agent_id": self.agent_id,
            "messages": self._log,
            "llm_settings": self.llm_settings or {},
            "history_summary": self._summary or "",
        }
        with open(self._fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 2: Commit**

```bash
git add core/conversation.py
git commit -m "feat: add history summary caching to Conversation"
```

---

### Task 3: Rewrite Smart Router Prompt + Code

**Files:**
- Modify: `neuros/smart_router/prompt.txt`
- Modify: `neuros/smart_router/code.py`

- [ ] **Step 1: Rewrite prompt.txt**

Replace entire contents of `neuros/smart_router/prompt.txt`:

```
You are Neuro, an intelligent AI assistant. Analyze the user's message
and route it by calling exactly one tool.

## Use `reply_directly` for:
- Greetings, thanks, goodbyes
- Knowledge questions ("what is X", "explain Y", "how does Z work")
- Opinions, advice, math, conversation, follow-ups
- Questions about your skills/capabilities
- Anything answerable from general knowledge
- DEFAULT when uncertain — most messages should be direct replies

## Use `invoke_skill` for:
- Explicit action requests: "lock my PC", "take screenshot", "open explorer"
- Code generation: "write a function", "create a script", "build an app"
- File/project operations: "create file X", "read file Y", "list files"
- Neuro/skill creation: "create a neuro", "make a new skill"
- Explicit delegation: "ask openclaw", "use the planner"

## Reply rules:
- Lead with the answer, no preamble
- 1-3 sentences for simple questions, longer for explanations
- No filler: skip "Sure!", "Great question!", "I'd be happy to"
- Reference conversation context naturally

## Available skills:
{{skills}}

## Recent conversation:
{{history}}

## User message:
{{text}}
```

- [ ] **Step 2: Rewrite code.py to use context assembler**

Replace entire contents of `neuros/smart_router/code.py`:

```python
"""
Smart Router — decides reply vs skill invocation using native tool calling.
Uses the context assembler for optimized token usage.
"""
import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "reply_directly",
            "description": "Reply to the user directly. Use for greetings, knowledge questions, conversation, advice, and anything answerable without performing an action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": "The response text to send to the user"
                    }
                },
                "required": ["reply"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_skill",
            "description": "Invoke a neuro skill to perform an action. Use only when the user explicitly requests a concrete action like generating code, writing files, or controlling the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The exact skill name from the available skills list"
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters required by the skill"
                    }
                },
                "required": ["skill"]
            }
        }
    },
]


async def run(state, **kwargs):
    llm = state["__llm"]
    system_prompt = state.get("__prompt", "")

    # Use context from assembler if available, fall back to kwargs
    history = kwargs.get("history", state.get("__router_history", ""))
    text = kwargs.get("text", "")
    skills = kwargs.get("skills", state.get("__router_skills", ""))

    final_system = (
        system_prompt
        .replace("{{skills}}", str(skills))
        .replace("{{history}}", str(history))
        .replace("{{text}}", str(text))
    )

    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": text},
    ]

    try:
        result = await llm.agenerate_with_tools(messages, TOOLS)
    except Exception as e:
        err = str(e)
        print(f"[SmartRouter] LLM error: {e}")
        if "429" in err or "rate" in err.lower():
            provider = getattr(llm, "provider", "configured provider")
            model = getattr(llm, "model", "configured model")
            return {
                "action": "reply",
                "reply": f"Rate limit reached on `{provider}` / `{model}`. Please retry in a moment or switch provider with /provider.",
            }
        return {"action": "reply", "reply": f"Something went wrong: {err[:120]}"}

    # Parse tool call
    if "tool_calls" in result and result["tool_calls"]:
        call = result["tool_calls"][0]
        fn_name = call["name"]
        args = call.get("arguments", {})

        if fn_name == "reply_directly":
            return {
                "action": "reply",
                "reply": args.get("reply", "I'm not sure how to respond."),
                "skill": None,
                "params": {},
            }

        if fn_name == "invoke_skill":
            return {
                "action": "skill",
                "reply": None,
                "skill": args.get("skill", ""),
                "params": args.get("params", {}),
            }

    # Fallback: plain text response
    content = result.get("content", "")
    if content:
        return {"action": "reply", "reply": content, "skill": None, "params": {}}

    return {"action": "reply", "reply": "I'm not sure how to respond."}
```

- [ ] **Step 3: Commit**

```bash
git add neuros/smart_router/prompt.txt neuros/smart_router/code.py
git commit -m "feat: rewrite smart router with context-aware prompts and cleaner tool calling"
```

---

### Task 4: Rewrite Reply Prompts

**Files:**
- Modify: `neuros/reply/prompt.txt`
- Modify: `neuros/reply/code.py`
- Modify: `neuros/code_reply/prompt.txt`
- Modify: `neuros/code_reply/code.py`

- [ ] **Step 1: Rewrite reply/prompt.txt**

Replace entire contents of `neuros/reply/prompt.txt`:

```
You are Neuro, a helpful and knowledgeable AI assistant.

## Personality:
- Direct and clear — lead with the answer, not filler
- Concise: 1-3 sentences for simple questions, more for explanations
- Reference prior conversation naturally when relevant
- Use markdown for code blocks and structured content
- No fluff: never start with "Sure!", "Absolutely!", "Great question!"

## Guidelines:
- Answer knowledge questions accurately and directly
- For code questions, include working examples
- When the user is vague, make a reasonable interpretation rather than asking
- If you don't know something, say so briefly
```

- [ ] **Step 2: Rewrite reply/code.py to use context assembler**

Replace entire contents of `neuros/reply/code.py`:

```python
"""Reply neuro — generates conversational responses with context awareness."""

async def run(state, *, text):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    conv = state.get("__conv")

    # Build context: prefer assembled context, fall back to raw history
    if conv:
        from core.context import build_reply_context, ensure_history_summary
        try:
            await ensure_history_summary(conv, llm)
        except Exception:
            pass  # summarization failure is non-fatal
        ctx = build_reply_context(conv)
        hist = ctx["history"]
    else:
        hist = state.get("__history", "")

    prompt = "\n\n".join(filter(None, [
        system,
        f"Conversation:\n{hist}" if hist else None,
        f"user: {text}",
        "assistant:",
    ])).strip()

    stream_cb = state.get("__stream_cb")
    answer = ""

    if stream_cb:
        for chunk in llm.stream_text(prompt, ""):
            answer += chunk
            await stream_cb(chunk)
    else:
        answer = await llm.agenerate_text(prompt, "")

    return {"reply": answer, "__streamed": bool(stream_cb)}
```

- [ ] **Step 3: Rewrite code_reply/prompt.txt**

Replace entire contents of `neuros/code_reply/prompt.txt`:

```
You are Neuro, a code-aware AI assistant.

## Personality:
- Technical and precise — like talking to a senior engineer
- Concise: summarize what was done, highlight important details
- Include file paths and code snippets when referencing operations
- No fluff: never start with "Sure!", "Absolutely!", "Great question!"

## When summarizing operations:
- List files created/modified with their paths
- Highlight any errors or warnings
- Suggest next steps if appropriate
```

- [ ] **Step 4: Rewrite code_reply/code.py to use context assembler**

Replace entire contents of `neuros/code_reply/code.py`:

```python
"""Code Reply — contextual response about code operations performed."""

async def run(state, *, text=None):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    conv = state.get("__conv")
    user_text = text or state.get("goal", "")

    # Build conversation context
    if conv:
        from core.context import build_reply_context, ensure_history_summary
        try:
            await ensure_history_summary(conv, llm)
        except Exception:
            pass
        ctx = build_reply_context(conv)
        hist = ctx["history"]
    else:
        hist = state.get("__history", "")

    # Gather operation results from execution state
    ops = []
    written = state.get("file_path") or state.get("__written_files")
    if written:
        ops.append(f"Files written: {written if isinstance(written, str) else ', '.join(written)}")
    read_content = state.get("content") or state.get("__read_content")
    if read_content and isinstance(read_content, str):
        ops.append(f"File content:\n{read_content[:2000]}")
    result = state.get("result") or state.get("output")
    if result and isinstance(result, str):
        ops.append(f"Result:\n{result[:2000]}")
    ops_context = "\n".join(ops)

    prompt = "\n\n".join(filter(None, [
        system,
        f"Conversation:\n{hist}" if hist else None,
        f"Operations performed:\n{ops_context}" if ops_context else None,
        f"user: {user_text}",
        "assistant:",
    ])).strip()

    stream_cb = state.get("__stream_cb")
    answer = ""

    if stream_cb:
        for chunk in llm.stream_text(prompt, ""):
            answer += chunk
            await stream_cb(chunk)
    else:
        answer = await llm.agenerate_text(prompt, "")

    return {"reply": answer, "__streamed": bool(stream_cb)}
```

- [ ] **Step 5: Commit**

```bash
git add neuros/reply/prompt.txt neuros/reply/code.py neuros/code_reply/prompt.txt neuros/code_reply/code.py
git commit -m "feat: rewrite reply neuros with personality, context assembly, and history summarization"
```

---

### Task 5: Rewrite Planner Prompts

**Files:**
- Modify: `neuros/planner/prompt.txt`
- Modify: `neuros/planner/code.py`
- Modify: `neuros/code_planner/prompt.txt`
- Modify: `neuros/code_planner/code.py`

- [ ] **Step 1: Planner prompt.txt is already updated (from earlier work). Verify it reads correctly.**

Current `neuros/planner/prompt.txt` should contain tool-calling-aware instructions. If it still references JSON output, replace with:

```
You are Neuro's task planner. Given a user request, create a
step-by-step execution plan using available skills.

You MUST call exactly one tool.

## Rules:
1. Each step = one skill invocation (atomic, single action)
2. Only use skills from the provided catalogue
3. Include a reply/summary step at the end using the reply neuro
4. Bias toward action — pick reasonable defaults over asking
5. Maximum 1 clarifying question, then just act
6. For vague responses ("whatever", "you decide") — pick defaults and proceed
```

- [ ] **Step 2: Update planner/code.py to use context assembler**

In `neuros/planner/code.py`, replace the context building section (lines 96-103) with:

```python
    # ── Build messages for tool calling ───────────────────────────
    conv = state.get("__conv")
    if conv:
        from core.context import build_planner_context
        env_state = state.get("__env_state")
        ctx = build_planner_context(conv, [{"name": n, "desc": ""} for n in (catalogue or [])], env_state)
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nConversation context: {ctx['history']}"
        if ctx.get("env_context"):
            context_str += f"\nEnvironment: {ctx['env_context']}"
    else:
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nConversation history: {hist}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context_str},
    ]
```

- [ ] **Step 3: Code planner prompt.txt is already updated. Verify.**

Current `neuros/code_planner/prompt.txt` should reference tool calling. If not, replace with:

```
You are Neuro's code planner. Create step-by-step execution plans
for code generation and project scaffolding tasks.

You MUST call exactly one tool.

## Available code neuros:
- code_project_manager: Create a project folder in /home/ubuntu/emptyWorkspace
- code_file_write: Write file content (params: filepath, content, mode)
- code_file_read: Read a file (params: filepath)
- code_file_list: List directory contents
- code_reply: Summarize what was done

## Rules:
1. Each step = one neuro call
2. Only use neuros from the provided catalogue
3. Output limit is 8,192 tokens — split files >150 lines into multiple writes
4. Generate complete, runnable code — no TODO placeholders
5. Always end with a code_reply step to summarize
6. Bias toward action — pick reasonable defaults
```

- [ ] **Step 4: Update code_planner/code.py similarly**

In `neuros/code_planner/code.py`, replace the context building (lines 125-131) with:

```python
    conv = state.get("__conv")
    if conv:
        from core.context import build_planner_context
        env_state = state.get("__env_state")
        ctx = build_planner_context(conv, [{"name": n, "desc": ""} for n in (catalogue or [])], env_state)
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nIntent: {intent or 'not specified'}\nContext: {ctx['history']}"
    else:
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nIntent: {intent or 'not specified'}"

    context_str += "\n\nIMPORTANT: Output limit is 8,192 tokens. For large files (>150 lines), split into multiple code_file_write steps. Generate complete, runnable code."
```

- [ ] **Step 5: Commit**

```bash
git add neuros/planner/prompt.txt neuros/planner/code.py neuros/code_planner/prompt.txt neuros/code_planner/code.py
git commit -m "feat: rewrite planner prompts with context assembly and clearer instructions"
```

---

### Task 6: Integrate Context Assembler into Brain

**Files:**
- Modify: `core/brain.py`

- [ ] **Step 1: Replace raw history building with context assembler calls**

In `core/brain.py`, find the history building section (around line 289-296):

```python
        # pass the full conversation history instead of just the last 10 turns
        hist = "\n".join(f"{m['sender']}: {m['text']}"
                        for m in conv.history())  # no arg = all messages

        # build a simple neuros list for the LLM
        dev = self.dev_flag.get(cid, False)
        neuros = self.factory.describe(cid) if dev else self.factory.describe()
        neuros_md = "\n".join(f"- **{t['name']}**: {t['desc']}" for t in neuros)
```

Replace with:

```python
        from core.context import build_router_context, build_skills_compact, format_messages_full

        # Build neuros list
        dev = self.dev_flag.get(cid, False)
        neuros = self.factory.describe(cid) if dev else self.factory.describe()
        neuros_md = "\n".join(f"- **{t['name']}**: {t['desc']}" for t in neuros)

        # Build context for router (compact — only last 5 messages)
        router_ctx = build_router_context(conv, neuros)

        # Full history still needed for planner/executor fallback
        hist = format_messages_full(conv.history())
```

- [ ] **Step 2: Pass router context to smart_router call**

Find the smart_router call (around line 351-358):

```python
        router_out = await self.factory.run(
            "smart_router",
            shared_state,
            history=hist,
            text=user_text,
            skills=neuros_md,
        )
```

Replace with:

```python
        router_out = await self.factory.run(
            "smart_router",
            shared_state,
            history=router_ctx["history"],
            text=user_text,
            skills=router_ctx["skills"],
        )
```

- [ ] **Step 3: Add `__conv` and `__cid` to shared_state**

In the `shared_state` dict (around line 302), add these two keys:

```python
            "__conv": conv,
            "__cid": cid,
```

This lets the context assembler inside neuros access the conversation object for summarization.

- [ ] **Step 4: Publish router rationale as debug event**

After the router returns (after line that sets `action`), add:

```python
        print(f"[BRAIN] Router returned: action={action}, skill={router_out.get('skill')}")
        await self._pub(cid, "debug", {
            "stage": "router",
            "action": action,
            "skill": router_out.get("skill"),
            "rationale": str(router_out.get("reply", ""))[:100] if action == "reply" else f"Invoking {router_out.get('skill')}",
        })
```

- [ ] **Step 5: Commit**

```bash
git add core/brain.py
git commit -m "feat: integrate context assembler into brain — router gets compact context, reply gets full"
```

---

### Task 7: Upgrade Neuro Descriptions

**Files:**
- Modify: 10 neuro `conf.json` files

- [ ] **Step 1: Upgrade key neuro descriptions**

Replace the `"description"` field in each conf.json:

**`neuros/code_file_write/conf.json`:**
```json
"description": "Write or append content to a file in the active project. Use when the user asks to create, write, or modify files. Parameters: filepath (relative path within project), content (the file text), mode ('write' to create/overwrite, 'append' to add to existing). For generated code files exceeding 150 lines, split across multiple calls."
```

**`neuros/code_file_read/conf.json`:**
```json
"description": "Read and display the contents of a text file from the active project. Use when the user asks to see, read, or inspect a file. Parameters: filepath (relative path within project). Returns the file content as text."
```

**`neuros/code_file_list/conf.json`:**
```json
"description": "List files in the active project directory using a glob pattern. Use when the user asks to see what files exist or browse the project structure. Parameters: pattern (glob like '**/*.py', defaults to '*'). Returns a list of matching file paths."
```

**`neuros/code_project_manager/conf.json`:**
```json
"description": "Create or switch the active project under /home/ubuntu/emptyWorkspace. Use when the user wants to start a new project or work in an existing one. Parameters: project_name (the folder name). Creates the directory if it doesn't exist."
```

**`neuros/neuro_list/conf.json`:**
```json
"description": "List all available neuros/skills with their descriptions. Use when the user asks what you can do, what skills are available, or wants to see capabilities. Takes no parameters."
```

**`neuros/reply/conf.json`:**
```json
"description": "Generate a conversational text response using the LLM. Use for general chat, knowledge questions, and any response that doesn't require executing a specific skill. Parameters: text (the user's message to respond to)."
```

**`neuros/code_reply/conf.json`:**
```json
"description": "Generate a code-aware response that summarizes operations performed during task execution. Use as the final step in code generation plans to tell the user what was created or modified. Parameters: text (the user's original request)."
```

**`neuros/openclaw_delegate/conf.json`:**
```json
"description": "Delegate a task to the OpenClaw web automation agent. Use when the user wants browser automation, web scraping, or web-based actions. You MUST refine the user's request into a precise instruction for a web agent. Parameters: task (clear instruction), session_id (conversation ID)."
```

**`neuros/screen_lock_ubuntu/conf.json`:**
```json
"description": "Lock the screen on the Ubuntu system. Use when the user asks to lock their computer, screen, or workstation. Takes no parameters."
```

**`neuros/code_planner/conf.json`:**
```json
"description": "Plan file and folder scaffolding for code generation tasks. Use for complex code requests that need multiple files or steps. Creates a DAG execution plan using available code neuros. Parameters: goal (what to build), catalogue (available neuros)."
```

- [ ] **Step 2: Commit**

```bash
git add neuros/*/conf.json
git commit -m "feat: upgrade neuro descriptions to 3-4 sentence behavior specs"
```

---

### Task 8: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Restart backend**

```bash
kill $(lsof -ti :7001) 2>/dev/null
sleep 2
PORT=7001 /home/ubuntu/neurocomputer/venv/bin/python server.py > /tmp/dev_backend_new.log 2>&1 &
sleep 4
tail -3 /tmp/dev_backend_new.log
```

- [ ] **Step 2: Test router — simple greeting**

```bash
CID=$(curl -s -X POST http://localhost:7001/conversation -H 'Content-Type: application/json' -d '{"agent_id":"neuro"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:7001/chat/send -H 'Content-Type: application/json' -d "{\"conversation_id\":\"$CID\",\"message\":\"hello\",\"agent_id\":\"neuro\"}"
sleep 8
grep "handle returned" /tmp/dev_backend_new.log | tail -1
```

Expected: `brain.handle returned: Hello! How can I help you?` (or similar concise greeting)

- [ ] **Step 3: Test router — knowledge question**

```bash
curl -s -X POST http://localhost:7001/chat/send -H 'Content-Type: application/json' -d "{\"conversation_id\":\"$CID\",\"message\":\"what is recursion\",\"agent_id\":\"neuro\"}"
sleep 8
grep "handle returned" /tmp/dev_backend_new.log | tail -1
```

Expected: Direct reply explaining recursion (no skill invocation)

- [ ] **Step 4: Test context — reply references history**

```bash
curl -s -X POST http://localhost:7001/chat/send -H 'Content-Type: application/json' -d "{\"conversation_id\":\"$CID\",\"message\":\"can you give me an example of that\",\"agent_id\":\"neuro\"}"
sleep 8
grep "handle returned" /tmp/dev_backend_new.log | tail -1
```

Expected: Reply references recursion (from previous message), not a generic response

- [ ] **Step 5: Test skill routing**

```bash
curl -s -X POST http://localhost:7001/chat/send -H 'Content-Type: application/json' -d "{\"conversation_id\":\"$CID\",\"message\":\"lock my computer\",\"agent_id\":\"neuro\"}"
sleep 5
grep "Router returned\|handle returned" /tmp/dev_backend_new.log | tail -2
```

Expected: Router returns `action=skill, skill=screen_lock_ubuntu`

- [ ] **Step 6: Check token usage is reasonable**

```bash
grep "BaseBrain.*chat.completions" /tmp/dev_backend_new.log | tail -5
```

Verify router calls use the compact model, not full conversation dumps.

- [ ] **Step 7: Commit any fixes from testing**

```bash
git add -A
git commit -m "fix: adjustments from end-to-end testing"
```

---
