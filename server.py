#!/usr/bin/env python3
import asyncio
import base64
import json
import logging
import os
import sys
import threading
import time
import uuid
import websockets
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Load environment variables FIRST
from dotenv import load_dotenv

load_dotenv(override=True)

# OpenClaw environment
OPENCLAW_WS_URL = os.getenv("OPENCLAW_WS_URL", "ws://127.0.0.1:18789").rstrip("/")
OPENCLAW_GATEWAY_TOKEN = (os.getenv("OPENCLAW_GATEWAY_TOKEN", "").strip())
OPENCLAW_IDENTITY_PATH = os.getenv("OPENCLAW_IDENTITY_PATH", "~/.openclaw/identity/device.json")

# OpenCode environment
OPENCODE_SERVER_URL = os.getenv("OPENCODE_SERVER_URL", "http://127.0.0.1:14096").rstrip("/")

# FastAPI imports
from fastapi import FastAPI, WebSocket, BackgroundTasks, Query, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from openai import OpenAI

# Neuro imports
from core.brain import Brain
from core.pubsub import hub
from core.voice_manager import voice_manager
from core.stt import transcribe_audio
from core.agent_manager import agent_manager
from core.conversation import Conversation
from core.db import db
from core.chat_handler import chat_manager
from core.llm_registry import get_default_llm_settings, get_provider_catalog, normalize_provider
from core import model_library
from core import tmux_manager
from core.terminal_ws import PtyBridge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable LiveKit Debug Logs
logging.getLogger("livekit").setLevel(logging.DEBUG)
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins.silero").setLevel(logging.DEBUG)  # For VAD
logging.getLogger("livekit.plugins.openai").setLevel(logging.DEBUG)  # For STT

# Create FastAPI app
app = FastAPI(title="Neuro Server")

# Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Attach IDE / neuro-library routes (/api/ide/*, /api/neuros*, /api/modify, etc.)
from core.ide_api import register_ide_routes
register_ide_routes(app)

# ----------------------------------------------------------------------------------
# Agent API Endpoints
# ----------------------------------------------------------------------------------

@app.get("/agents")
async def list_agents():
    """List all running agents."""
    return {"agents": agent_manager.list_agents()}

@app.get("/agents/types")
async def list_agent_types():
    """List available agent types that can be created."""
    return {"types": agent_manager.list_agent_types()}

@app.post("/agents/{agent_type}")
async def create_or_switch_agent(agent_type: str):
    """Create a new agent of the specified type, or switch to existing one."""
    try:
        agent = agent_manager.switch_to_agent_type(agent_type)
        return {"agent_id": agent.agent_id, "name": agent.config.name, "description": agent.config.description}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/agents/{agent_id}/switch")
async def switch_agent(agent_id: str):
    """Switch the active agent."""
    if agent_manager.switch_active_agent(agent_id):
        return {"active_agent_id": agent_id, "agents": agent_manager.list_agents()}
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

@app.get("/agents/active")
async def get_active_agent():
    """Get or create the currently active agent."""
    agent = agent_manager.ensure_default_agent()
    return {"agent_id": agent.agent_id, "name": agent.config.name}

# ----------------------------------------------------------------------------------
# Upwork Job Capture API Endpoints
# ----------------------------------------------------------------------------------

import os
import json

UPWORK_DIR = Path("upwork/projects")

@app.post("/upwork/capture")
async def capture_frame(body: dict):
    """Save a raw OCR frame to a job."""
    job_slug = body.get("job_slug", "").strip().replace(" ", "_").lower()
    frame_text = body.get("frame_text", "").strip()
    url = body.get("url", "")

    if not job_slug:
        raise HTTPException(status_code=400, detail="job_slug required")
    if not frame_text:
        raise HTTPException(status_code=400, detail="frame_text required")

    job_dir = UPWORK_DIR / job_slug
    job_dir.mkdir(parents=True, exist_ok=True)

    frames_file = job_dir / "frames.json"
    if frames_file.exists():
        frames = json.loads(frames_file.read_text())
    else:
        frames = []

    frames.append({
        "text": frame_text,
        "url": url,
        "timestamp": datetime.now().isoformat()
    })

    frames_file.write_text(json.dumps(frames, indent=2, ensure_ascii=False))

    return {"saved": True, "frame_count": len(frames), "job_slug": job_slug}

@app.post("/upwork/finalize/{job_slug}")
async def finalize_job(job_slug: str):
    """Deduplicate frames and create structured meta.json using LLM."""
    job_slug = job_slug.strip()
    job_dir = UPWORK_DIR / job_slug
    frames_file = job_dir / "frames.json"

    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_slug} not found")
    if not frames_file.exists():
        raise HTTPException(status_code=400, detail="No frames captured yet")

    frames = json.loads(frames_file.read_text())

    # Simple deduplication
    unique_lines = set()
    deduplicated = []
    for frame in frames:
        lines = frame.get("text", "").split("\n")
        for line in lines:
            line = line.strip()
            if len(line) < 5:
                continue
            if line not in unique_lines:
                unique_lines.add(line)
                deduplicated.append(line)

    combined_text = "\n".join(deduplicated[:200])  # Limit to 200 lines

    # Use LLM to extract structured data
    from core.base_brain import BaseBrain
    upwork_llm = BaseBrain("gpt-4o-mini", temperature=0.3)

    system_prompt = """Extract job data from Upwork posting. Return JSON:
{"title": "...", "company": "...", "budget": "...", "skills": [...], "description": "...", "verdict": "worth_apply|skip|maybe", "red_flags": [...]}
If not found use null."""

    try:
        raw = upwork_llm.generate_json(combined_text[:8000], system_prompt)
        job_data = json.loads(raw)
    except Exception as e:
        job_data = {"error": str(e), "title": job_slug}

    meta = {
        "job_slug": job_slug,
        "title": job_data.get("title", job_slug),
        "company": job_data.get("company", "Not specified"),
        "budget": job_data.get("budget", "Not specified"),
        "skills": job_data.get("skills", []),
        "description": job_data.get("description", combined_text[:3000]),
        "url": frames[0].get("url", "") if frames else "",
        "verdict": job_data.get("verdict", "unknown"),
        "red_flags": job_data.get("red_flags", []),
        "captured_at": datetime.now().isoformat(),
        "frame_count": len(frames),
        "unique_lines": len(unique_lines)
    }

    meta_file = job_dir / "meta.json"
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    # Save combined raw text
    (job_dir / "raw_combined.txt").write_text(combined_text)

    return {"ok": True, "job_slug": job_slug, "meta": {k: v for k, v in meta.items() if k not in ["description"]}}

@app.get("/upwork/jobs")
async def list_jobs():
    """List all saved Upwork jobs."""
    if not UPWORK_DIR.exists():
        return {"jobs": [], "count": 0}

    jobs = []
    for job_slug in os.listdir(UPWORK_DIR):
        job_dir = UPWORK_DIR / job_slug
        if not job_dir.is_dir():
            continue

        meta_file = job_dir / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            jobs.append({
                "slug": job_slug,
                "title": meta.get("title", "Unknown"),
                "company": meta.get("company", ""),
                "budget": meta.get("budget", ""),
                "verdict": meta.get("verdict", ""),
                "captured_at": meta.get("captured_at", "")
            })
        else:
            frames_file = job_dir / "frames.json"
            if frames_file.exists():
                frames = json.loads(frames_file.read_text())
                jobs.append({
                    "slug": job_slug,
                    "title": f"[Draft] {job_slug}",
                    "status": "not_finalized",
                    "frame_count": len(frames)
                })

    jobs.sort(key=lambda x: x.get("captured_at", ""), reverse=True)
    return {"jobs": jobs, "count": len(jobs)}

@app.get("/upwork/job/{job_slug}")
async def get_job(job_slug: str):
    """Get full job details."""
    job_dir = UPWORK_DIR / job_slug.strip()
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_slug} not found")

    meta = {}
    meta_file = job_dir / "meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())

    proposal = ""
    proposal_file = job_dir / "proposal.md"
    if proposal_file.exists():
        proposal = proposal_file.read_text()

    raw = ""
    raw_file = job_dir / "raw_combined.txt"
    if raw_file.exists():
        raw = raw_file.read_text()[:5000]

    return {
        "slug": job_slug,
        "meta": meta,
        "proposal": proposal,
        "raw_preview": raw
    }

# In-memory storage of Brain instances per conversation
brains: Dict[str, Brain] = {}

# Active screen sharing tasks: {user_id: asyncio.Task}
_screen_tasks: Dict[str, asyncio.Task] = {}

# Audio storage directory
AUDIO_DIR = Path("uploads/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for audio serving
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


@app.post("/tts")
async def tts(body: dict):
    text = str(body.get("text", "") or "").strip()
    cid = str(body.get("cid", "") or "").strip()
    voice = str(body.get("voice", "alloy") or "alloy").strip() or "alloy"
    msg_id = str(body.get("msg_id", "") or "").strip()  # optional: server-side message index to update

    if not text:
        raise HTTPException(status_code=400, detail="text required")
    if not cid:
        raise HTTPException(status_code=400, detail="cid required")

    try:
        file_id = uuid.uuid4().hex[:12]
        audio_filename = f"tts_{cid}_{file_id}.mp3"
        audio_path = AUDIO_DIR / audio_filename

        def _render_tts():
            elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
            elevenlabs_voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip()

            if elevenlabs_key and elevenlabs_voice:
                try:
                    import httpx
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(
                            f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice}",
                            headers={
                                "xi-api-key": elevenlabs_key,
                                "Content-Type": "application/json",
                                "Accept": "audio/mpeg",
                            },
                            json={
                                "text": text,
                                "model_id": "eleven_turbo_v2_5",
                                "voice_settings": {
                                    "stability": 0.5,
                                    "similarity_boost": 0.75,
                                },
                            },
                        )
                        response.raise_for_status()
                        with open(audio_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                        logger.info(f"[TTS] Generated audio via ElevenLabs for conversation {cid}")
                        return
                except Exception as e:
                    logger.warning(f"[TTS] ElevenLabs failed, falling back to OpenAI: {e}")

            client = OpenAI()
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=voice,
                input=text,
                response_format="mp3",
            )
            speech.stream_to_file(str(audio_path))
            logger.info(f"[TTS] Generated audio via OpenAI for conversation {cid}")

        await asyncio.to_thread(_render_tts)
        audio_url = f"/audio/{audio_filename}"

        # Persist audio_url to DB so voice box survives tab refresh
        if msg_id:
            try:
                import aiosqlite
                async with aiosqlite.connect(db.db_path) as conn:
                    await conn.execute(
                        "UPDATE messages SET audio_url = ?, type = 'voice' WHERE id = ?",
                        (audio_url, msg_id)
                    )
                    await conn.commit()
                    logger.info(f"[TTS] Saved audio_url to DB for msg {msg_id}")
            except Exception as e:
                logger.warning(f"[TTS] Could not update DB msg: {e}")

        return {"audio_url": audio_url}
    except Exception as e:
        logger.error(f"[TTS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------
# Neuro API Endpoints
# ----------------------------------------------------------------------------------

# Monkey patch the Executor.run method to explicitly emit replies
from core.executor import Executor

_original_run = Executor.run

async def _patched_run(self):
    conv = self.state.get("__conv")   # may be None in tests
    node  = self.flow["start"]
    nodes = self.flow["nodes"]

    # Wrap the pub method to intercept 'assistant' messages
    original_pub = self.pub
    async def pub_wrapper(topic, data):
        """
        The Executor already publishes any assistant reply; emitting another
        one here causes duplicate panels in the CLI.  Therefore we now simply
        relay every node.* event unchanged.
        """
        await original_pub(topic, data)
    
    self.pub = pub_wrapper
    
    while node:
        spec = nodes[node]                        # {neuro, params, next}
        await self.pub("node.start", {"id": node, "neuro": spec["neuro"]})
        try:
            out = await self.factory.run(
                spec["neuro"],
                self.state,
                **spec.get("params", {}),
            )
            self.state.update(out)
        except Exception as e:
            # ❶ standardised error payload
            err_obj = {
                "error": type(e).__name__,
                "message": str(e),
            }
            # ❷ push a visible assistant message
            await hub.queue(self.state.get("__cid", "default")).put({
                "topic": "assistant",
                "data": f"⚠️ {spec['neuro']} failed: {e}",
            })
            # ❸ still emit node.done so the client's wait logic un-blocks
            await self.pub("node.done", {"id": node, "out": err_obj})
            # ❹ re-raise so Executor/run() can abort the remaining DAG cleanly
            raise
        if conv and "reply" in out and isinstance(out["reply"], str):
            conv.add("assistant", out["reply"])
            await self.pub("assistant", out["reply"])   # 🔥 send to clients
        await self.pub("node.done", {"id": node, "out": out})
        node = spec.get("next")

# Apply the monkey patch
Executor.run = _patched_run

async def _handle_and_emit(cid: str, text: str, agent_id: str = None):
    """Run Agent.handle_message and push its textual reply (if any) to the hub."""
    # If agent_id not provided, look it up from the conversation file
    if not agent_id:
        conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
        if conv_file.exists():
            with open(conv_file) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    agent_id = data.get("agent_id")
                    logger.info(f"Looked up agent_id from conversation {cid}: {agent_id}")

    # Get or create the agent
    if agent_id:
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            # Try looking up by type (handles case where frontend passes type like "neuro" instead of instance ID)
            agent = agent_manager.get_agent_by_type(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found, using default")
            agent = agent_manager.ensure_default_agent()
    else:
        agent = agent_manager.ensure_default_agent()

    logger.info(f"Routing message for {cid} to agent: {agent.agent_id}")

    # Use try-except to handle any errors in the agent processing
    try:
        # Pass the original requested agent_id so brain can route to the correct delegate
        # (e.g. "opencode" → opencode_delegate), even if the agent manager fell back to default.
        effective_agent_id = agent_id or agent.agent_id
        logger.info(f"Processing message from {cid} with agent {effective_agent_id}: {text}")
        reply = await agent.handle_message(cid, text, agent_id=effective_agent_id)
        logger.info(f"Agent reply for {cid}: {reply}")

        if reply:
            q = hub.queue(cid)
            # Only send task.done for immediate replies (not for async tasks)
            if not reply.startswith("🚀"):
                await q.put({"topic": "task.done", "data": {}})
                logger.info(f"Sent task.done for {cid} (immediate reply)")
    except Exception as e:
        logger.error(f"Error processing message for {cid}: {str(e)}")
        # Notify the client of the error
        q = hub.queue(cid)
        await q.put({"topic": "assistant", "data": f"Error processing your request: {str(e)}"})


@app.post("/chat")
async def chat(body: dict, bt: BackgroundTasks):
    cid = body.get("cid") or uuid.uuid4().hex
    text = body["text"]
    agent_id = body.get("agent_id")  # Optional agent_id
    # publish user message event
    await hub.queue(cid).put({"topic": "user", "data": text})
    # handle asynchronously and emit reply when done
    bt.add_task(_handle_and_emit, cid, text, agent_id)
    return {"cid": cid, "agent_id": agent_manager.active_agent_id}

# ----------------------------------------------------------------------------------
# Chat Send (HTTP-based, reliable message sending from mobile)
# ----------------------------------------------------------------------------------
_chat_tasks: dict[str, asyncio.Task] = {}   # cid → background _process task

@app.post("/chat/send")
async def chat_send(body: dict):
    """
    Reliable HTTP endpoint for sending chat messages from mobile.
    Response is delivered via LiveKit DataChannel (brain._pub).
    """
    cid = body.get("cid") or body.get("conversation_id")
    text = body.get("text") or body.get("message", "")
    agent_id = body.get("agent_id")
    origin = body.get("origin", "app")
    if not cid or not text:
        raise HTTPException(status_code=400, detail="cid and text are required")

    # Save user message to DB
    await db.add_message(conversation_id=cid, sender="user", msg_type="text", content=text)

    # Resolve agent_id from conversation file if not provided
    if not agent_id:
        conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
        if conv_file.exists():
            try:
                with open(conv_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        agent_id = data.get("agent_id")
            except Exception:
                pass

    # Process in background — brain._pub sends response via DataChannel
    async def _process():
        try:
            room = await chat_manager.get_or_create_room(cid, agent_id or "neuro")
            # Ensure agent is connected BEFORE processing (waits for reconnect if needed)
            if not room._agent_started:
                await room.start_agent()
            else:
                await room._ensure_agent_connected()
            # Wait for brain to be ready
            await asyncio.wait_for(room._agent_ready.wait(), timeout=15.0)
            brain = room._brain if room._brain else Brain()
            logger.info(f"[chat/send] Processing cid={cid} agent={agent_id or 'neuro'}: {text[:60]}")
            response = await brain.handle(cid=cid, user_text=text, agent_id=agent_id or "neuro")
            logger.info(f"[chat/send] brain.handle returned: {response}")
            if not response:
                if room:
                    from core.chat_handler import ChatMessage as CM
                    err = CM(msg_type="text", sender="agent", content="⚠️ No response generated.")
                    await room.send_to_all(err, topic="agent_response")
        except Exception as e:
            import traceback
            logger.error(f"[chat/send] Error processing: {e}\n{traceback.format_exc()}")

    # Cancel any previous in-flight task for this conversation
    prev = _chat_tasks.pop(cid, None)
    if prev and not prev.done():
        prev.cancel()
    task = asyncio.create_task(_process())
    _chat_tasks[cid] = task
    task.add_done_callback(lambda t: _chat_tasks.pop(cid, None))
    return {"status": "ok", "cid": cid}


@app.post("/chat/{cid}/cancel")
async def cancel_chat(cid: str):
    """Cancel an in-progress chat task for a conversation."""
    cancelled = []

    # 1. Cancel the top-level _process task (covers direct replies, router, etc.)
    process_task = _chat_tasks.pop(cid, None)
    if process_task and not process_task.done():
        process_task.cancel()
        cancelled.append("process")

    # 2. Cancel the executor task if one is running (covers skill/planner paths)
    room = await chat_manager.get_room(cid)
    if room:
        brain = getattr(room, "_brain", None)
        if brain and cid in brain.tasks:
            task, state = brain.tasks[cid]
            if not task.done():
                task.cancel()
                cancelled.append("executor")
            brain.tasks.pop(cid, None)

    logger.info(f"[chat/cancel] Cancelled {cancelled} for cid={cid}")
    return {"status": "cancelled", "cancelled": cancelled, "cid": cid}


# ----------------------------------------------------------------------------------
# Chat API Endpoints (LiveKit DataChannel)
# ----------------------------------------------------------------------------------

@app.post("/chat/token")
async def get_chat_token(body: dict):
    """
    Generate a LiveKit token for joining a chat room.
    
    This replaces the old WebSocket /ws/{cid} endpoint with LiveKit DataChannel.
    """
    conversation_id = body.get("conversation_id")
    participant_name = body.get("participant_name", "mobile_user")
    is_agent = body.get("is_agent", False)
    agent_id = body.get("agent_id")  # May be passed directly by the client
    
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    
    # If agent_id not given, look it up from the conversation file so we always
    # create the room with the correct agent (not defaulting to 'neuro').
    if not agent_id:
        conv_file = Path(__file__).parent / "conversations" / f"{conversation_id}.json"
        if conv_file.exists():
            try:
                with open(conv_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        agent_id = data.get("agent_id")
                        logger.info(f"[ChatToken] Resolved agent_id from conversation file: {agent_id}")
            except Exception as e:
                logger.warning(f"[ChatToken] Could not read conversation file: {e}")
    
    try:
        token_data = await chat_manager.generate_token(
            conversation_id=conversation_id,
            participant_name=participant_name,
            is_agent=is_agent,
            agent_id=agent_id or "neuro",
        )
        return token_data
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{conversation_id}/messages")
async def get_chat_messages(
    conversation_id: str,
    limit: int = 50,
    before: Optional[str] = None
):
    """Get messages for a conversation."""
    messages = await db.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        before=before,
    )
    return {"messages": messages}

@app.post("/chat/{conversation_id}/read")
async def mark_messages_read(conversation_id: str, body: dict):
    """Mark messages as read (for future read receipts feature)."""
    message_id = body.get("message_id")
    return {"status": "ok", "message_id": message_id}

# ----------------------------------------------------------------------------------
# Conversations API Endpoints
# ----------------------------------------------------------------------------------

@app.get("/conversations")
async def list_conversations(agent_id: str = None, project_id: str = None, agency_id: str = None, workspace_id: str = None):
    """List all conversations, optionally filtered by agent_id and/or project_id.
    Use project_id='none' to list conversations in NoProject (no project assigned)."""
    conv_dir = Path(__file__).parent / "conversations"
    # Normalise project_id filter: 'none' → None sentinel for NoProject
    filter_project = project_id  # None means "no filter", 'none' means NoProject
    allowed_project_ids = None
    # Support both workspace_id (new) and agency_id (legacy)
    ws_id = workspace_id or agency_id
    if ws_id:
        agency_projects = await db.list_projects(workspace_id=ws_id)
        allowed_project_ids = {project["id"] for project in agency_projects if project.get("id")}

    conversations = []
    if conv_dir.exists():
        for f in conv_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    # Handle both old format (array) and new format (object)
                    if isinstance(data, list):
                        messages = data
                        conv_agent_id = None
                        conv_project_id = None
                    else:
                        messages = data.get("messages", [])
                        conv_agent_id = data.get("agent_id")
                        conv_project_id = data.get("project_id")  # None = NoProject

                    # Filter by agent_id if provided
                    if agent_id and conv_agent_id != agent_id:
                        continue

                    # Filter by project_id if provided.
                    # The default workspace's MainProject (``main-default``)
                    # doubles as the bucket for any legacy orphan convs
                    # whose ``project_id`` is still null, so convs with
                    # ``conv_project_id is None`` pass this filter too.
                    if filter_project is not None:
                        if filter_project == "none":
                            if conv_project_id is not None:
                                continue
                        elif filter_project == "main-default":
                            if conv_project_id not in (None, "main-default"):
                                continue
                        else:
                            if conv_project_id != filter_project:
                                continue
                    elif allowed_project_ids is not None:
                        if conv_project_id not in allowed_project_ids:
                            continue

                    title = data.get("title", "New Chat") if isinstance(data, dict) else "New Chat"
                    if title == "New Chat" and messages:
                        for msg in messages:
                            if msg.get("sender") == "user" and msg.get("text"):
                                title = msg["text"][:50]
                                break
                            elif msg.get("sender") == "assistant" and msg.get("text"):
                                title = msg["text"][:50]
                                break
                    conversations.append({
                        "id": f.stem,
                        "title": title,
                        "lastMessage": messages[-1].get("text", "") if messages else "",
                        "updatedAt": datetime.now().isoformat(),
                        "createdAt": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "agentId": conv_agent_id,
                        "projectId": conv_project_id,
                        "workdir": data.get("workdir") if isinstance(data, dict) else None,
                    })
            except Exception:
                pass
    conversations.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return conversations

@app.get("/conversation/{cid}")
async def get_conversation(cid: str):
    """Get a specific conversation — reads from DB first, falls back to JSON file."""
    # Try database first (has accurate voice/audio metadata)
    db_messages = await db.get_messages(cid, limit=200)
    if db_messages:
        conv_info = await db.get_conversation(cid)
        agent_id = conv_info.get("agent_id") if conv_info else None
        formatted = []
        for msg in db_messages:
            is_voice = msg.get("type") == "voice"
            audio_url = msg.get("audio_url")
            formatted.append({
                "id": msg.get("id", ""),
                "role": "user" if msg.get("sender") == "user" else "assistant",
                "content": msg.get("content", ""),
                "timestamp": msg.get("created_at", ""),
                "audioUrl": audio_url,
                "isVoice": is_voice or (audio_url is not None and audio_url != ""),
            })
        project_id = conv_info.get("project_id") if conv_info else None
        conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
        llm_settings = get_default_llm_settings()
        workdir = None
        if conv_file.exists():
            try:
                with open(conv_file) as fp:
                    file_data = json.load(fp)
                    if isinstance(file_data, dict):
                        llm_settings.update(file_data.get("llm_settings") or {})
                        workdir = file_data.get("workdir")
            except Exception:
                pass
        return {"id": cid, "agentId": agent_id, "projectId": project_id, "workdir": workdir, "llmSettings": llm_settings, "messages": formatted}

    # Fallback to JSON file for older conversations
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if conv_file.exists():
        with open(conv_file) as fp:
            data = json.load(fp)
            if isinstance(data, list):
                messages = data
                agent_id = None
                project_id = None
            else:
                messages = data.get("messages", [])
                agent_id = data.get("agent_id")
                project_id = data.get("project_id")

            formatted = []
            for i, msg in enumerate(messages):
                formatted.append({
                    "id": str(i),
                    "role": "user" if msg.get("sender") == "user" else "assistant",
                    "content": msg.get("text", ""),
                    "timestamp": msg.get("ts", ""),
                    "audioUrl": msg.get("audio_url"),
                    "isVoice": msg.get("is_voice", False)
                })
            llm_settings = data.get("llm_settings") or get_default_llm_settings()
            workdir = data.get("workdir") if isinstance(data, dict) else None
            return {"id": cid, "agentId": agent_id, "projectId": project_id, "workdir": workdir, "llmSettings": llm_settings, "messages": formatted}
    return {"id": cid, "agentId": None, "projectId": None, "workdir": None, "llmSettings": get_default_llm_settings(), "messages": []}

@app.post("/conversation")
async def create_conversation(body: dict = None):
    """Create a new conversation"""
    cid = uuid.uuid4().hex
    agent_id = None
    title = "New Chat"
    llm_settings = get_default_llm_settings()
    workspace_hint: Optional[str] = None
    raw_project_id: Optional[str] = None
    if body:
        agent_id = body.get("agent_id")
        workspace_hint = body.get("workspace_id") or body.get("agency_id")
        raw_project_id = body.get("project_id")
        if body.get("title"):
            title = body["title"]
        provider = body.get("llm_provider")
        model = body.get("llm_model")
        if provider:
            llm_settings["provider"] = normalize_provider(provider)
        if model:
            llm_settings["model"] = str(model).strip()
    project_id = await _resolve_project_or_main(raw_project_id, workspace_hint)
    workdir = body.get("workdir") if body else None
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    with open(conv_file, "w") as fp:
        json.dump({"agent_id": agent_id, "messages": [], "title": title, "project_id": project_id, "workdir": workdir, "llm_settings": llm_settings}, fp)
    return {"id": cid, "cid": cid, "title": title, "agentId": agent_id, "projectId": project_id, "workdir": workdir, "llmSettings": llm_settings}

@app.patch("/conversation/{cid}")
async def update_conversation(cid: str, body: dict = None):
    """Update a conversation (e.g., rename)"""
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if conv_file.exists():
        with open(conv_file) as fp:
            data = json.load(fp)
        
        # Update fields
        if body:
            if "title" in body:
                data["title"] = body["title"]
            if "agent_id" in body:
                data["agent_id"] = body["agent_id"]
            if "workdir" in body:
                data["workdir"] = body["workdir"]
            if "llm_provider" in body or "llm_model" in body:
                settings = data.get("llm_settings") or get_default_llm_settings()
                if "llm_provider" in body and body["llm_provider"]:
                    settings["provider"] = normalize_provider(body["llm_provider"])
                if "llm_model" in body and body["llm_model"]:
                    settings["model"] = str(body["llm_model"]).strip()
                data["llm_settings"] = settings
        
        with open(conv_file, "w") as fp:
            json.dump(data, fp, indent=2)
        
        return {"success": True, "conversation": data}
    return {"success": False, "error": "Conversation not found"}


@app.get("/llm/providers")
async def list_llm_providers():
    return {
        "providers": get_provider_catalog(),
        "default": get_default_llm_settings(),
    }


@app.get("/model-library")
async def get_model_library():
    """Return the full named-model library: aliases + roles."""
    return model_library.load_library()


@app.put("/model-library")
async def put_model_library(body: dict):
    """Replace the whole library atomically. Validates aliases/roles cross-refs."""
    try:
        return model_library.save_library(body or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/opencode/model")
async def set_opencode_model(body: dict):
    """Change the active model on OpenCode serve: update config, clear sessions, restart server."""
    import subprocess
    provider_id = body.get("provider", "")
    model_id = body.get("model", "")
    if not provider_id or not model_id:
        raise HTTPException(status_code=400, detail="provider and model required")

    new_model = f"{provider_id}/{model_id}"

    # 1) Update config file
    config_path = Path.home() / ".config" / "opencode" / "opencode.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            if cfg.get("model") == new_model:
                return {"model": new_model, "status": "ok", "changed": False}
            cfg["model"] = new_model
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    # 2) Clear session cache (sessions are model-locked)
    session_map = Path(__file__).parent / "data" / "opencode_sessions.json"
    if session_map.exists():
        try:
            with open(session_map, "w") as f:
                json.dump({}, f)
        except Exception:
            pass
    # Clear in-memory cache
    try:
        from neuros.opencode_delegate import code as oc_mod
        if oc_mod._sessions is not None:
            oc_mod._sessions.clear()
    except Exception:
        pass

    # 3) Restart opencode serve
    subprocess.run(["pkill", "-f", "opencode serve"], capture_output=True)
    await asyncio.sleep(1)
    port = OPENCODE_SERVER_URL.split(":")[-1]
    subprocess.Popen(
        ["opencode", "serve", "--port", port],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # 4) Wait for healthy
    import aiohttp
    for _ in range(15):
        await asyncio.sleep(1)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{OPENCODE_SERVER_URL}/global/health",
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as r:
                    if r.status == 200:
                        return {"model": new_model, "status": "ok", "changed": True}
        except Exception:
            pass

    return {"model": new_model, "status": "ok", "changed": True, "warning": "server may still be starting"}


@app.get("/opencode/providers")
async def list_opencode_providers():
    """Proxy OpenCode serve's provider/model list, transformed to NeuroComputer format."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{OPENCODE_SERVER_URL}/config/providers",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                if r.status != 200:
                    return {"providers": [], "default": {"provider": "", "model": ""}}
                data = await r.json()
    except Exception:
        return {"providers": [], "default": {"provider": "", "model": ""}}

    providers = []
    for p in data.get("providers", []):
        model_ids = list(p.get("models", {}).keys())
        if not model_ids:
            continue
        providers.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "envKey": "",
            "available": True,
            "defaultModel": model_ids[0],
            "models": model_ids,
        })

    default_cfg = data.get("default", {})
    default_provider = default_cfg.get("provider", providers[0]["id"] if providers else "")
    default_model = default_cfg.get("model", providers[0]["defaultModel"] if providers else "")

    return {
        "providers": providers,
        "default": {"provider": default_provider, "model": default_model},
    }


@app.get("/conversation/{cid}/llm")
async def get_conversation_llm(cid: str):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    settings = get_default_llm_settings()
    selection_type = None
    if conv_file.exists():
        with open(conv_file) as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                settings.update(data.get("llm_settings") or {})
                raw_sel = data.get("selection_type")
                selection_type = raw_sel if raw_sel in ("raw", "role") else None
    settings["selection_type"] = selection_type
    return settings


@app.patch("/conversation/{cid}/llm")
async def update_conversation_llm(cid: str, body: dict):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    with open(conv_file) as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        data = {"messages": data}

    settings = data.get("llm_settings") or get_default_llm_settings()
    provider = body.get("provider")
    model = body.get("model")
    if provider:
        settings["provider"] = normalize_provider(provider)
    if model:
        settings["model"] = str(model).strip()
    data["llm_settings"] = settings
    # Raw pick: user explicitly chose provider+model → overrides role pin.
    data["selection_type"] = "raw"
    logger.info(
        f"[LLM] Conversation {cid} settings updated to provider={settings.get('provider')} "
        f"model={settings.get('model')} selection_type=raw"
    )

    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)

    cache_entry = dict(settings)
    cache_entry["selection_type"] = "raw"

    for agent in agent_manager.agents.values():
        try:
            agent.brain.llm_settings[cid] = dict(cache_entry)
            if cid in getattr(agent.brain, "convs", {}):
                agent.brain.convs[cid]._selection_type = "raw"
                agent.brain.convs[cid].llm_settings = dict(settings)
        except Exception:
            pass

    try:
        room = await chat_manager.get_room(cid)
        if room and room._brain:
            room._brain.llm_settings[cid] = dict(cache_entry)
            if cid in getattr(room._brain, "convs", {}):
                room._brain.convs[cid]._selection_type = "raw"
                room._brain.convs[cid].llm_settings = dict(settings)
            logger.info(
                f"[LLM] Refreshed active chat room brain for {cid} to "
                f"provider={settings.get('provider')} model={settings.get('model')}"
            )
    except Exception as e:
        logger.warning(f"[LLM] Could not refresh chat room brain for {cid}: {e}")

    try:
        vs = voice_manager._sessions.get(cid)
        if vs and vs.brain:
            vs.brain.llm_settings[cid] = dict(cache_entry)
            if cid in getattr(vs.brain, "convs", {}):
                vs.brain.convs[cid]._selection_type = "raw"
                vs.brain.convs[cid].llm_settings = dict(settings)
            logger.info(
                f"[LLM] Refreshed active voice brain for {cid} to "
                f"provider={settings.get('provider')} model={settings.get('model')}"
            )
    except Exception as e:
        logger.warning(f"[LLM] Could not refresh voice brain for {cid}: {e}")

    return settings


@app.get("/conversation/{cid}/role")
async def get_conversation_role(cid: str):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    session_role: Optional[str] = None
    selection_type: Optional[str] = None
    if conv_file.exists():
        with open(conv_file) as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                session_role = data.get("session_role") or None
                raw_sel = data.get("selection_type")
                selection_type = raw_sel if raw_sel in ("raw", "role") else None
    return {"session_role": session_role, "selection_type": selection_type}


@app.patch("/conversation/{cid}/role")
async def update_conversation_role(cid: str, body: dict):
    """Set or clear the session role for a conversation.

    Body: ``{"session_role": "<slug>"}`` to set, ``{"session_role": null}`` to clear.
    Mirrors resolved provider/model into in-memory brains so the next message
    picks it up without restart (same pattern as ``PATCH .../llm``).
    """
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    raw = body.get("session_role")
    slug = raw.strip() if isinstance(raw, str) and raw.strip() else None

    resolved = None
    if slug is not None:
        if slug not in model_library.list_roles():
            raise HTTPException(status_code=400, detail=f"Unknown role '{slug}'")
        resolved = model_library.resolve_role(slug)
        if not resolved:
            raise HTTPException(status_code=400, detail=f"Role '{slug}' has no resolvable alias")

    with open(conv_file) as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        data = {"messages": data}
    data["session_role"] = slug
    # Role pick: explicit role wins over raw pick. Clearing role falls back
    # to whatever raw pick / default was previously honored — preserve the
    # prior selection_type rather than wiping it, so raw memory survives a
    # role clear.
    if slug is not None:
        data["selection_type"] = "role"
    elif data.get("selection_type") == "role":
        data["selection_type"] = None
    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)

    logger.info(
        f"[ROLE] Conversation {cid} session_role → {slug!r} "
        f"selection_type={data.get('selection_type')}"
    )

    # Mirror resolved settings into live brains so the next turn uses them.
    # On clear, drop the cache so the legacy path / default resolves on next call.
    cache_entry = dict(resolved) if resolved else None
    if cache_entry is not None:
        cache_entry["selection_type"] = "role"
    new_sel = data.get("selection_type")

    def _mirror(brain):
        if cache_entry is not None:
            brain.llm_settings[cid] = dict(cache_entry)
        else:
            brain.llm_settings.pop(cid, None)
        if cid in getattr(brain, "convs", {}):
            brain.convs[cid]._session_role = slug
            brain.convs[cid]._selection_type = new_sel

    for agent in agent_manager.agents.values():
        try:
            _mirror(agent.brain)
        except Exception:
            pass
    try:
        room = await chat_manager.get_room(cid)
        if room and room._brain:
            _mirror(room._brain)
    except Exception as e:
        logger.warning(f"[ROLE] Could not refresh chat room brain for {cid}: {e}")

    try:
        vs = voice_manager._sessions.get(cid)
        if vs and vs.brain:
            _mirror(vs.brain)
            logger.info(f"[ROLE] Refreshed active voice brain for {cid}")
    except Exception as e:
        logger.warning(f"[ROLE] Could not refresh voice brain for {cid}: {e}")

    return {"session_role": slug, "resolved": resolved}


# ── Terminal tabs ─────────────────────────────────────────────────────

def _terminal_tab_to_dict(cid: str, data: dict) -> dict:
    return {
        "id": cid,
        "cid": cid,
        "type": data.get("type") or "chat",
        "title": data.get("title") or "terminal",
        "workspace_id": data.get("workspace_id")
                        or data.get("agency_id")
                        or "default",
        "project_id": data.get("project_id") or None,
        "tmux_session": data.get("tmux_session") or None,
        "workdir": data.get("workdir") or None,
        "created_at": data.get("created_at"),
    }


@app.get("/terminal/capabilities")
async def terminal_capabilities():
    ok = tmux_manager.tmux_available()
    return {
        "available": ok,
        "reason": None if ok else "tmux binary not found on host PATH",
    }


@app.post("/terminal")
async def create_terminal(body: dict):
    if not tmux_manager.tmux_available():
        raise HTTPException(status_code=501, detail="tmux not installed")

    workspace_id = (body.get("workspace_id") or body.get("agency_id")
                    or "default")
    project_id = body.get("project_id") or "main-default"
    title = (body.get("title") or "").strip() or "terminal"
    workdir = (body.get("workdir") or "").strip() or None
    tmux_session = (body.get("tmux_session") or "").strip() or None

    created_new = False
    if not tmux_session:
        tmux_session = tmux_manager.make_session_name(workspace_id, project_id)
        created_new = True

    try:
        tmux_manager.new_session(tmux_session, workdir)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    cid = uuid.uuid4().hex
    now = int(time.time())
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    conv_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "agent_id": None,
        "title": title,
        "type": "terminal",
        "workspace_id": workspace_id,
        "project_id": project_id,
        "tmux_session": tmux_session,
        "workdir": workdir,
        "created_at": now,
        "messages": [],
        "llm_settings": {},
        "session_role": None,
        "selection_type": None,
    }
    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)

    out = _terminal_tab_to_dict(cid, data)
    out["created_new"] = created_new
    return out


@app.get("/terminal")
async def list_terminals(project_id: Optional[str] = None,
                         agency_id: Optional[str] = None):
    conv_dir = Path(__file__).parent / "conversations"
    out = []
    for p in conv_dir.glob("*.json"):
        try:
            with open(p) as fp:
                data = json.load(fp)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if (data.get("type") or "chat") != "terminal":
            continue
        if project_id and data.get("project_id") != project_id:
            continue
        if agency_id and (data.get("workspace_id")
                          or data.get("agency_id")) != agency_id:
            continue
        out.append(_terminal_tab_to_dict(p.stem, data))
    out.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
    return out


@app.get("/terminal/sessions")
async def terminal_sessions(project_id: Optional[str] = None,
                            agency_id: Optional[str] = None):
    ws = agency_id or "default"
    proj = project_id or "main-default"
    prefix = f"neuro-{tmux_manager._slug(ws)}-{tmux_manager._slug(proj)}-"
    return tmux_manager.list_sessions(prefix=prefix)


@app.get("/terminal/{cid}")
async def get_terminal(cid: str):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        raise HTTPException(status_code=404, detail="not a terminal tab")
    return _terminal_tab_to_dict(cid, data)


@app.patch("/terminal/{cid}")
async def patch_terminal(cid: str, body: dict):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        raise HTTPException(status_code=404, detail="not a terminal tab")
    if "title" in body:
        t = (body.get("title") or "").strip()
        if t:
            data["title"] = t
    if "tmux_session" in body:
        name = (body.get("tmux_session") or "").strip() or None
        if name:
            if not tmux_manager.session_exists(name):
                workdir = data.get("workdir")
                try:
                    tmux_manager.new_session(name, workdir)
                except RuntimeError as e:
                    raise HTTPException(status_code=500, detail=str(e))
            data["tmux_session"] = name
    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)
    return _terminal_tab_to_dict(cid, data)


@app.websocket("/terminal/ws/{cid}")
async def terminal_ws(websocket: WebSocket, cid: str):
    await websocket.accept()
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        try:
            await websocket.send_text(json.dumps({
                "type": "error", "msg": "conversation not found"
            }))
        finally:
            await websocket.close()
        return
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        try:
            await websocket.send_text(json.dumps({
                "type": "error", "msg": "not a terminal tab"
            }))
        finally:
            await websocket.close()
        return
    name = data.get("tmux_session")
    workdir = data.get("workdir")
    if not name:
        try:
            await websocket.send_text(json.dumps({
                "type": "error", "msg": "tab has no tmux_session"
            }))
        finally:
            await websocket.close()
        return
    # Auto-recreate if the session died (e.g. host reboot).
    if not tmux_manager.session_exists(name):
        try:
            tmux_manager.new_session(name, workdir)
        except RuntimeError as e:
            try:
                await websocket.send_text(json.dumps({
                    "type": "error", "msg": f"tmux start failed: {e}"
                }))
            finally:
                await websocket.close()
            return
    bridge = PtyBridge(websocket, name)
    try:
        await bridge.run()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("[terminal_ws] bridge error for %s", cid)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.delete("/terminal/{cid}")
async def delete_terminal(cid: str, kill_session: int = 0):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    name = data.get("tmux_session")
    conv_file.unlink()
    killed = False
    if kill_session and name:
        killed = tmux_manager.kill_session(name)
    return {"ok": True, "killed": killed, "tmux_session": name}


@app.delete("/conversation/{cid}")
async def delete_conversation(cid: str):
    """Delete a conversation"""
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if conv_file.exists():
        conv_file.unlink()
        return {"success": True}
    return {"success": False, "error": "Conversation not found"}


# ----------------------------------------------------------------------------------
# Project API Endpoints
# ----------------------------------------------------------------------------------

CONV_DIR = Path(__file__).parent / "conversations"

def _conv_project_id(cid: str) -> Optional[str]:
    """Read project_id from a conversation JSON file."""
    f = CONV_DIR / f"{cid}.json"
    if not f.exists():
        return None
    try:
        with open(f) as fp:
            return json.load(fp).get("project_id")
    except Exception:
        return None

def _set_conv_project_id(cid: str, project_id: Optional[str]):
    """Write project_id into a conversation JSON file."""
    f = CONV_DIR / f"{cid}.json"
    if not f.exists():
        return
    with open(f) as fp:
        data = json.load(fp)
    data["project_id"] = project_id
    with open(f, "w") as fp:
        json.dump(data, fp, indent=2)

def _is_main_project(pid: Optional[str]) -> bool:
    return isinstance(pid, str) and pid.startswith("main-")


async def _resolve_project_or_main(
    raw: Optional[str],
    workspace_hint: Optional[str] = None,
) -> str:
    """Return a concrete project id. Inputs that mean 'no explicit project'
    (``None`` / ``""`` / ``"none"``) resolve to the MainProject of the hinted
    workspace (falls back to the ``default`` workspace's MainProject)."""
    if raw and raw != "none":
        return raw
    wid = workspace_hint or "default"
    return await db.get_main_project_id(wid)

# ── Workspaces (formerly Agencies) ────────────────────────────────────────

@app.get("/workspaces")
async def list_workspaces():
    """List all workspaces."""
    return await db.list_workspaces()

@app.post("/workspaces")
async def create_workspace(body: dict):
    workspace_id = body.get("id") or uuid.uuid4().hex[:12]
    ws = await db.create_workspace(
        workspace_id=workspace_id,
        name=body.get("name", "New Workspace"),
        description=body.get("description", ""),
        color=body.get("color", "#8B5CF6"),
        emoji=body.get("emoji", "🏢"),
        agents=body.get("agents", ["neuro"]),
        default_agent=body.get("default_agent", "neuro"),
        theme=body.get("theme", "cosmic"),
    )
    # A fresh workspace gets its own MainProject so the default-project
    # guarantees hold from day one.
    await db.seed_main_projects([workspace_id])
    return ws

@app.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    result = await db.get_workspace(workspace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return result

@app.patch("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, body: dict):
    await db.update_workspace(workspace_id, **body)
    return await db.get_workspace(workspace_id)

@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    await db.delete_workspace(workspace_id)
    return {"status": "ok"}

# Legacy aliases
@app.get("/agencies")
async def list_agencies_legacy():
    return await db.list_workspaces()

@app.post("/agencies")
async def create_agency_legacy(body: dict):
    body.setdefault("id", uuid.uuid4().hex[:12])
    return await db.create_workspace(workspace_id=body["id"], name=body.get("name", "New Workspace"),
        description=body.get("description", ""), color=body.get("color", "#8B5CF6"),
        emoji=body.get("emoji", "🏢"), agents=body.get("agents", ["neuro"]),
        default_agent=body.get("default_agent", "neuro"))

# ── Projects ─────────────────────────────────────────────────────────────

@app.get("/projects")
async def list_projects(agency_id: str = None, workspace_id: str = None):
    """List projects in a workspace. Each workspace has a MainProject row
    (id ``main-{workspaceId}``) that serves as the default bucket for
    conversations without an explicit project — it's returned first."""
    ws_id = workspace_id or agency_id
    projects = await db.list_projects(workspace_id=ws_id)
    # Count conversations per project (scan JSON files). We also fold
    # legacy project_id=null (pre-migration) into the default workspace's
    # MainProject count so the badge in the UI still matches reality.
    project_counts: Dict[str, int] = {}
    legacy_null_count = 0
    if CONV_DIR.exists():
        for f in CONV_DIR.glob("*.json"):
            try:
                with open(f) as fp:
                    pid = json.load(fp).get("project_id")
                if pid:
                    if ws_id:
                        project = await db.get_project(pid)
                        if not project or project.get("workspaceId") != ws_id:
                            continue
                    project_counts[pid] = project_counts.get(pid, 0) + 1
                else:
                    legacy_null_count += 1
            except Exception:
                pass
    default_main_id = "main-default"
    if legacy_null_count and (ws_id is None or ws_id == "default"):
        project_counts[default_main_id] = project_counts.get(default_main_id, 0) + legacy_null_count
    for p in projects:
        p["conversationCount"] = project_counts.get(p["id"], 0)
    return projects

@app.post("/projects")
async def create_project(body: dict):
    """Create a new project."""
    name = body.get("name", "New Project")
    description = body.get("description", "")
    color = body.get("color", "#8B5CF6")
    agents = body.get("agents", ["neuro"])
    workspace_id = body.get("workspace_id") or body.get("agency_id")
    project = await db.create_project(
        name=name,
        description=description,
        color=color,
        agents=agents,
        workspace_id=workspace_id,
    )
    project["conversationCount"] = 0
    return project

@app.get("/projects/{pid}")
async def get_project(pid: str):
    """Get a project by ID."""
    project = await db.get_project(pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.patch("/projects/{pid}")
async def update_project(pid: str, body: dict):
    """Update a project's name, description, color, or session_state."""
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
    if "workspaceId" in body:
        fields["workspace_id"] = body["workspaceId"]
    elif "agencyId" in body:
        fields["workspace_id"] = body["agencyId"]
    await db.update_project(pid, **fields)
    return {"success": True}

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


@app.delete("/projects/{pid}")
async def delete_project(pid: str):
    """Delete a project. The MainProject row of a workspace is non-deletable
    (it's the fallback bucket for orphaned conversations in that workspace).
    Regular-project conversations fall back to their workspace's MainProject."""
    if _is_main_project(pid):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a workspace's MainProject",
        )
    project = await db.get_project(pid)
    target_main = await db.get_main_project_id(
        (project or {}).get("workspaceId") or "default"
    )
    if CONV_DIR.exists():
        for f in CONV_DIR.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                if data.get("project_id") == pid:
                    data["project_id"] = target_main
                    with open(f, "w") as fp2:
                        json.dump(data, fp2, indent=2)
            except Exception:
                pass
    await db.delete_project(pid)
    return {"success": True, "fallbackProjectId": target_main}

async def _main_project_for_conv(cid: str) -> str:
    """Resolve the MainProject for the workspace that the conversation's
    current project lives in. Falls back to the default workspace when the
    conversation or its project doesn't expose a workspace."""
    try:
        f = CONV_DIR / f"{cid}.json"
        if f.exists():
            with open(f) as fp:
                conv = json.load(fp)
            current_pid = conv.get("project_id")
            if current_pid:
                proj = await db.get_project(current_pid)
                wid = (proj or {}).get("workspaceId") or "default"
                return await db.get_main_project_id(wid)
    except Exception:
        pass
    return await db.get_main_project_id("default")

@app.patch("/conversation/{cid}/project")
async def move_conversation_to_project(cid: str, body: dict):
    """Move a conversation to a different project. Passing ``null``/``"none"``
    routes the conversation to its workspace's MainProject."""
    raw = body.get("project_id")
    if raw in (None, "", "none"):
        target_pid = await _main_project_for_conv(cid)
    else:
        target_pid = raw
    _set_conv_project_id(cid, target_pid)
    return {"success": True, "cid": cid, "projectId": target_pid}

@app.post("/conversation/{cid}/fork")
async def fork_conversation(cid: str, body: dict):
    """Fork a conversation (full copy) into a target project."""
    raw_target = body.get("project_id")
    if raw_target in (None, "", "none"):
        target_pid = await _main_project_for_conv(cid)
    else:
        target_pid = raw_target
    src_file = CONV_DIR / f"{cid}.json"
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    with open(src_file) as fp:
        src_data = json.load(fp)

    new_cid = uuid.uuid4().hex
    new_data = {
        "agent_id": src_data.get("agent_id"),
        "title": f"Fork of {src_data.get('title', 'Chat')}",
        "messages": src_data.get("messages", []),
        "project_id": target_pid,
        "llm_settings": src_data.get("llm_settings") or get_default_llm_settings(),
    }
    new_file = CONV_DIR / f"{new_cid}.json"
    with open(new_file, "w") as fp:
        json.dump(new_data, fp, indent=2)

    # Also copy DB messages if they exist
    src_db_messages = await db.get_messages(cid, limit=1000)
    if src_db_messages:
        await db.get_or_create_conversation(new_cid, src_data.get("agent_id", "neuro"))
        for msg in src_db_messages:
            await db.add_message_with_id(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                conversation_id=new_cid,
                sender=msg["sender"],
                msg_type=msg["type"],
                content=msg.get("content"),
                audio_url=msg.get("audio_url"),
                duration_ms=msg.get("duration_ms"),
            )

    return {"success": True, "cid": new_cid, "projectId": target_pid}


# ----------------------------------------------------------------------------------
# Voice API Endpoints (LiveKit)
# ----------------------------------------------------------------------------------

@app.post("/voice/call")
async def voice_call_start(body: dict):
    """
    Start a full-duplex voice call for a conversation.

    Body: {"conversation_id": "...", "agent_id": "neuro"}
    Returns: {"token": "...", "url": "...", "room_name": "...", "conversation_id": "..."}
    """
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id required")
    agent_id = body.get("agent_id", "neuro")

    try:
        result = await voice_manager.start_call(conversation_id, agent_id)
        logger.info(f"Voice call started for conversation {conversation_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start voice call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start voice call: {e}")


@app.post("/voice/hangup")
async def voice_call_end(body: dict):
    """
    End a voice call.

    Body: {"conversation_id": "..."}
    """
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id required")

    await voice_manager.end_call(conversation_id)
    return {"status": "ended", "conversation_id": conversation_id}


@app.get("/voice/status/{conversation_id}")
async def voice_call_status(conversation_id: str):
    """Check if a voice call is active."""
    return {
        "active": voice_manager.is_active(conversation_id),
        "conversation_id": conversation_id,
    }


# Keep legacy endpoints for backward compatibility
@app.post("/voice/token")
async def voice_token(body: dict):
    """Legacy: create voice session by user_id. Redirects to start_call."""
    user_id = body.get("user_id") or uuid.uuid4().hex[:8]
    conversation_id = f"voice_{user_id}"
    try:
        result = await voice_manager.start_call(conversation_id)
        return result
    except Exception as e:
        logger.error(f"Failed to create voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/end")
async def voice_end(body: dict):
    """Legacy: end voice session by user_id."""
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    await voice_manager.end_call(f"voice_{user_id}")
    return {"status": "ended"}


@app.post("/screen/start")
async def start_screen_share(body: dict):
    """
    Start desktop screen sharing for the user.
    Body: {"user_id": "..."}
    """
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
        
    try:
        # Match the room name used by /voice/token → voice_manager.start_call,
        # which wraps user_id as conversation_id = f"voice_{user_id}" and then
        # creates the room as f"voice-{conversation_id}".
        conversation_id = f"voice_{user_id}"
        room_name = f"voice-{conversation_id}"
        # Generate unique identity for the screen sharer to avoid conflicts
        screen_identity = f"infinity-screen-{uuid.uuid4().hex[:4]}"
        
        # Room and Agent setup
        from core.voice_manager import voice_manager
        token = voice_manager._generate_token(room_name, screen_identity, is_agent=False)
        url = voice_manager._url
        
        if not url or not token:
             raise HTTPException(status_code=500, detail="LiveKit not configured")

        # Kill any existing stream task for this user
        global _screen_tasks
        if user_id in _screen_tasks:
            logger.info(f"[Screen] Cancelling old stream task for {user_id}")
            _screen_tasks[user_id].cancel()
            try:
                from core.display_controller import controller as _disp
                asyncio.create_task(_disp.session_end())
            except Exception as e:
                logger.warning(f"[Screen] session_end on cancel failed: {e}")
            # We don't necessarily need to await it here to avoid blocking the request
            # but we could.
        
        # Start streaming in background
        from core.desktop_stream import start_desktop_stream
        from livekit import rtc
        
        async def _stream_task():
            room = rtc.Room()
            try:
                await room.connect(url, token)
                logger.info(f"[Screen] Connected to {room_name} as {screen_identity}")
                await start_desktop_stream(room, room_name)
            except asyncio.CancelledError:
                logger.info(f"[Screen] Stream task cancelled for {user_id}")
            except Exception as e:
                logger.error(f"[Screen] Connection failed: {e}")
            finally:
                await room.disconnect()
                if _screen_tasks.get(user_id) and _screen_tasks[user_id].get_name() == screen_identity:
                     _screen_tasks.pop(user_id, None)

        # Fire and forget (it runs as long as room is active or until error)
        task = asyncio.create_task(_stream_task())
        task.set_name(screen_identity)
        _screen_tasks[user_id] = task

        # Move mouse to current display center so pointer is visible immediately
        try:
            import mss, subprocess
            sct = mss.mss()
            # Move mouse to center of display on start to ensure initial visibility
            mon = sct.monitors[_current_display_index]
            cx = mon['left'] + mon['width'] // 2
            cy = mon['top'] + mon['height'] // 2
            subprocess.run(["xdotool", "mousemove", str(cx), str(cy)], check=False)
            sct.close()
            logger.info(f"[Screen] Moved pointer to display {_current_display_index} center ({cx},{cy})")
        except Exception as e:
            logger.warning(f"[Screen] Could not move pointer on start: {e}")

        return {"status": "started", "room": room_name, "identity": screen_identity}
        
    except Exception as e:
        logger.error(f"Failed to start screen share: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen/view")
async def update_screen_view(body: dict):
    """
    Update the zoom and pan for screen sharing.
    Body: {
        "user_id": "...",
        "zoom": 2.0,        # Optional: 1.0 = full screen, 2.0 = 2x zoom
        "pan_x": 0.5,       # Optional: 0.0 = left, 1.0 = right, 0.5 = center
        "pan_y": 0.5,       # Optional: 0.0 = top, 1.0 = bottom, 0.5 = center
        "reset": false      # Optional: reset to default view
    }
    """
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # Match the room naming used by /voice/token + /screen/start.
    room_name = f"voice-voice_{user_id}"

    from core.desktop_stream import update_view
    
    state = update_view(
        room_name,
        zoom=body.get("zoom"),
        pan_x=body.get("pan_x"),
        pan_y=body.get("pan_y"),
        rotation=body.get("rotation"),

        reset=body.get("reset", False)
    )
    
    return {
        "status": "updated",
        "zoom": state.zoom,
        "pan_x": state.pan_x,
        "pan_y": state.pan_y
    }


# Global display state
_current_display_index = 1  # Start with primary monitor (index 1)


@app.post("/display/normalise")
async def normalise_display():
    """Reset every connected output's xrandr rotation to 'normal'.
    Safety hatch for when tablet-mode left a display stuck rotated."""
    try:
        from core.display_controller import controller as _disp
        await _disp.normalise()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[Display] normalise failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screen/switch-display")
async def switch_display():
    """
    Switch between multiple displays.
    Cycles through available displays: monitor 1, monitor 2, etc.
    """
    import mss
    import subprocess
    global _current_display_index

    try:
        sct = mss.mss()
        num_monitors = len(sct.monitors) - 1  # -1 because index 0 is "all"

        if num_monitors <= 1:
            return {"status": "single_display", "message": "Only one display available"}

        # Cycle to next display
        _current_display_index = (_current_display_index % num_monitors) + 1
        monitor = sct.monitors[_current_display_index]

        # Update the desktop stream if running
        from core.desktop_stream import set_current_monitor, update_mouse_controller_for_monitor
        set_current_monitor(_current_display_index)

        # Update mouse controller offset so window_focus uses the correct monitor
        offset = (monitor.get('left', 0), monitor.get('top', 0))
        update_mouse_controller_for_monitor(monitor['width'], monitor['height'], offset)

        # Move mouse to center of new monitor and click to focus a window there.
        # This solves issues where clicks might not register on a newly focused display.
        center_x = monitor['left'] + monitor['width'] // 2
        center_y = monitor['top'] + monitor['height'] // 2
        try:
            subprocess.run(["xdotool", "mousemove", str(center_x), str(center_y)], check=False)
            # Small delay then click to focus whatever window is under the cursor
            import time
            time.sleep(0.03)
            subprocess.run(["xdotool", "click", "1"], check=False)
            logger.info(f"[Display] Moved mouse and clicked to focus on monitor {_current_display_index}")
        except Exception as e:
            logger.warning(f"[Display] Failed to move/click mouse: {e}")

        logger.info(f"[Display] Switched to monitor {_current_display_index}: {monitor}")
        sct.close()

        return {
            "status": "switched",
            "display_index": _current_display_index,
            "monitor": monitor,
            "total_displays": num_monitors
        }
    except Exception as e:
        logger.error(f"[Display] Switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screen/displays")
async def get_displays():
    """Get list of available displays."""
    import mss
    try:
        sct = mss.mss()
        displays = []
        for i, mon in enumerate(sct.monitors):
            if i == 0:
                displays.append({"index": i, "name": "all", **mon})
            else:
                displays.append({"index": i, "name": f"monitor {i}", **mon})
        sct.close()
        return {"displays": displays, "current": _current_display_index}
    except Exception as e:
        logger.error(f"[Display] Get displays error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------------
# Voice Message API (Audio Recording + STT)
# ----------------------------------------------------------------------------------

@app.post("/transcribe")
async def transcribe_only(file: UploadFile = File(...)):
    """Transcribe audio and return the text. No DB writes, no brain
    routing — suitable for non-chat destinations like terminal stdin."""
    ext = Path(file.filename).suffix or ".webm"
    tmp_path = AUDIO_DIR / f"transcribe_{uuid.uuid4().hex[:8]}{ext}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(await file.read())
        text = await transcribe_audio(str(tmp_path))
        return {"text": (text or "").strip()}
    except Exception as e:
        logger.error(f"[Transcribe] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try: tmp_path.unlink()
        except Exception: pass


@app.post("/voice-message")
async def voice_message(
    file: UploadFile = File(...),
    cid: str = Form(...),
    agent_id: str = Form(None),
    origin: str = Form(None),
    bt: BackgroundTasks = None
):
    """
    Process voice message: save audio, transcribe, and send to Brain via LiveKit.
    
    Form data:
        - file: audio file (mp3, m4a, wav, webm)
        - cid: conversation ID
        - agent_id: optional agent ID
    
    Returns:
        {
            "message_id": "...",
            "transcription": "...",
            "audio_url": "/audio/...",
            "duration": 0.0
        }
    """
    try:
        # Generate unique message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        # Determine file extension
        ext = Path(file.filename).suffix or ".m4a"
        audio_filename = f"{cid}_{message_id}{ext}"
        audio_path = AUDIO_DIR / audio_filename
        
        # Save uploaded file
        logger.info(f"[VoiceMsg] Saving audio: {audio_filename}")
        with open(audio_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Transcribe using OpenAI Whisper
        logger.info(f"[VoiceMsg] Transcribing...")
        transcription = await transcribe_audio(str(audio_path))
        
        if not transcription.strip():
            transcription = "(No speech detected)"
        
        # Build audio URL (relative to server)
        audio_url = f"/audio/{audio_filename}"
        
        # Save to new database
        await db.add_message(
            conversation_id=cid,
            sender="user",
            msg_type="voice",
            content=transcription,
            audio_url=audio_url,
        )
        
        # Conv file save is handled by brain.handle() inside _handle_voice_message
        # (with audio_url and is_voice metadata passed through).

        # Process voice through brain and send response via DataChannel.
        # Run as background task so the HTTP response (with transcription) returns immediately.
        if bt:
            bt.add_task(_handle_voice_message, cid, transcription, agent_id, origin, audio_url)
        else:
            asyncio.create_task(_handle_voice_message(cid, transcription, agent_id, origin, audio_url))
        
        logger.info(f"[VoiceMsg] Complete: {transcription[:50]}...")
        
        return {
            "message_id": message_id,
            "transcription": transcription,
            "audio_url": audio_url,
        }
        
    except Exception as e:
        logger.error(f"[VoiceMsg] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_voice_message(cid: str, transcription: str, agent_id: str = None, origin: str = None, audio_url: str = None):
    """Process voice transcription through brain and send response via DataChannel.

    The user message is already saved to DB by the /voice-message endpoint.
    brain.handle() saves to conv JSON file (with voice metadata).
    This function: brain response → save agent reply to DB → send via DataChannel.
    """
    chat_room = None
    try:
        chat_room = await chat_manager.get_or_create_room(cid, agent_id or "neuro")

        if not chat_room._agent_started:
            logger.info(f"[VoiceMsg] Starting agent for voice message room: {cid}")
            await chat_room.start_agent()

        # Wait for agent/brain to be ready
        await asyncio.wait_for(chat_room._agent_ready.wait(), timeout=10.0)

        if not chat_room._brain:
            logger.error(f"[VoiceMsg] Brain not available for cid={cid}")
            return

        # Suppress hub to avoid duplicate delivery via old WebSocket path
        # brain._pub() still sends via LiveKit DataChannel, so no explicit send_to_all needed
        chat_room._brain._suppress_hub = True
        try:
            response_text = await chat_room._brain.handle(
                cid=cid,
                user_text=transcription,
                agent_id=agent_id or "neuro",
                audio_url=audio_url,
                is_voice=True,
            )
        finally:
            chat_room._brain._suppress_hub = False

        if response_text:
            logger.info(f"[VoiceMsg] Response delivered via DataChannel: {response_text[:50]}")
        else:
            logger.warning(f"[VoiceMsg] Brain returned empty response for cid={cid}")

    except Exception as e:
        logger.error(f"[VoiceMsg] Error handling voice message: {e}")
        if chat_room and chat_room._brain:
            chat_room._brain._suppress_hub = False


_voice_type_lock = threading.Lock()

def _type_text_sync(text: str):
    """Type text via xdotool in a thread-safe way. Splits into small chunks
    to avoid xdotool timeout/buffer issues with long text."""
    import subprocess as sp

    with _voice_type_lock:
        # Clear any stuck modifier keys first (prevents --clearmodifiers restore bug)
        sp.run(["xdotool", "keyup", "shift", "ctrl", "alt", "super"],
               check=False, capture_output=True, timeout=5)

        # Split text into chunks of ~200 chars at word boundaries
        chunk_size = 200
        pos = 0
        chunk_num = 0
        while pos < len(text):
            end = min(pos + chunk_size, len(text))
            if end < len(text):
                space_idx = text.rfind(" ", pos, end)
                if space_idx > pos:
                    end = space_idx + 1
            chunk = text[pos:end]
            chunk_num += 1
            logger.info(f"[VoiceType] xdotool chunk {chunk_num}: {len(chunk)} chars")
            result = sp.run(
                ["xdotool", "type", "--delay", "8", chunk],
                check=False, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.error(f"[VoiceType] xdotool failed (rc={result.returncode}): {result.stderr}")
            pos = end


@app.post("/voice-type")
async def voice_type(
    file: UploadFile = File(...),
    press_enter: bool = False,
):
    """
    Voice-to-Type: Transcribe audio and type the text at the current cursor position.
    Uses xdotool to simulate keyboard input on the desktop.
    If press_enter is True, presses Enter after all text is typed.
    """
    import subprocess

    try:
        # Save uploaded audio temporarily
        message_id = uuid.uuid4().hex[:12]
        ext = Path(file.filename).suffix or ".m4a"
        audio_filename = f"voice_type_{message_id}{ext}"
        audio_path = AUDIO_DIR / audio_filename

        with open(audio_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Transcribe full audio (Whisper handles up to 25MB / ~2hrs fine)
        logger.info("[VoiceType] Transcribing...")
        transcription = await transcribe_audio(str(audio_path))

        if not transcription.strip():
            return {"transcription": "", "typed": False}

        # Type the text using xdotool in a background thread.
        # Text is split into ~200-char chunks internally to prevent
        # xdotool from timing out or dropping text on long passages.
        logger.info(f"[VoiceType] Typing {len(transcription)} chars: {transcription[:80]}...")
        await asyncio.to_thread(_type_text_sync, transcription)

        # Optionally press Enter after all text is typed
        if press_enter:
            await asyncio.to_thread(
                subprocess.run,
                ["xdotool", "key", "Return"],
                check=False, capture_output=True, timeout=5
            )

        # Clean up temp audio file
        try:
            audio_path.unlink()
        except Exception:
            pass

        return {"transcription": transcription, "typed": True}

    except Exception as e:
        logger.error(f"[VoiceType] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot")
async def take_screenshot():
    """
    Capture the full screen, save as PNG, and copy to the X clipboard.
    After this, Ctrl+V will paste the screenshot into any app that accepts images.
    """
    import subprocess
    import mss
    from PIL import Image
    import io

    try:
        # Capture full screen
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # Full virtual screen
            screenshot = sct.grab(monitor)

        # Convert to PNG bytes
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        png_buffer = io.BytesIO()
        img.save(png_buffer, format="PNG")
        png_bytes = png_buffer.getvalue()

        # Also save to a temp file for xclip (xclip reads from stdin or file)
        screenshot_path = AUDIO_DIR / "screenshot_latest.png"
        with open(screenshot_path, "wb") as f:
            f.write(png_bytes)

        # Copy to X clipboard using xclip
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(screenshot_path)],
            check=False, capture_output=True, timeout=5
        )

        if result.returncode != 0:
            logger.warning(f"[Screenshot] xclip failed: {result.stderr.decode()}")
            # Fallback: try xsel
            subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=png_bytes,
                check=False, capture_output=True, timeout=5
            )

        logger.info(f"[Screenshot] Captured {screenshot.size[0]}x{screenshot.size[1]}, copied to clipboard")
        return {"success": True, "width": screenshot.size[0], "height": screenshot.size[1]}

    except Exception as e:
        logger.error(f"[Screenshot] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{cid}")
async def websocket_endpoint(ws: WebSocket, cid: str):
    logger.info(f"WebSocket connection requested for conversation: {cid}")
    await ws.accept()
    logger.info(f"WebSocket connection accepted for conversation: {cid}")
    q = hub.queue(cid)
    try:
        # Send initial connection confirmation
        await ws.send_text(json.dumps({"topic": "system", "data": "Connected to Neuro"}))
        logger.info(f"Sent initial connection message to client: {cid}")
        
        while True:
            ev = await q.get()
            logger.info(f"Sending event to client {cid}: {ev['topic']}")
            await ws.send_text(json.dumps(ev, default=str, ensure_ascii=False))
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {cid}")
    except Exception as e:
        logger.error(f"Error in WebSocket handling for {cid}: {str(e)}")
    finally:
        logger.info(f"WebSocket connection closed for conversation: {cid}")

# ----------------------------------------------------------------------------------
# OpenClaw Control API
# ----------------------------------------------------------------------------------

import httpx
import uuid
import sys
import os

# Global HTTP client to prevent port exhaustion (TIME_WAIT socket leaks)
_httpx_client = None

def get_httpx_client():
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=60.0)
    return _httpx_client

# OpenClaw state
openclaw_state: Dict[str, Any] = {
    "connected": False,
    "last_response": "",
    "last_error": "",
}

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    await db.init()
    # Seed default workspaces from config
    from core.workspace_configs import WORKSPACE_CONFIGS
    await db.seed_workspaces(WORKSPACE_CONFIGS)
    # Seed a MainProject for every workspace (default project for each).
    # Also migrates any orphaned projects (agency_id=NULL) onto the
    # `default` (Main Workspace) workspace.
    existing_workspaces = await db.list_workspaces()
    await db.seed_main_projects([w["id"] for w in existing_workspaces])
    logger.info("Starting background pollers...")
    asyncio.create_task(_global_openclaw_poller())

@app.on_event("shutdown")
async def shutdown_event():
    global _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
        _httpx_client = None


async def _global_openclaw_poller():
    global openclaw_state
    while True:
        if openclaw_state.get("connected"):
            ok = await _probe_openclaw()
            openclaw_state["connected"] = bool(ok)
            if not ok and not openclaw_state.get("last_error"):
                openclaw_state["last_error"] = "OpenClaw gateway not reachable"
        await asyncio.sleep(1)


@dataclass
class DeviceIdentity:
    device_id: str
    public_key_pem: str
    private_key_pem: str


def _load_device_identity(path: str = OPENCLAW_IDENTITY_PATH) -> DeviceIdentity:
    expanded = os.path.expanduser(path)
    try:
        with open(expanded, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise RuntimeError("Device identity missing. Approve a device first with openclaw devices.") from exc
    return DeviceIdentity(
        device_id=data["deviceId"],
        public_key_pem=data["publicKeyPem"],
        private_key_pem=data["privateKeyPem"],
    )


def _build_device_auth_payload(*, device_id: str, client_id: str, client_mode: str,
                              role: str, scopes: str, signed_at_ms: int,
                              token: str, nonce: str) -> str:
    return "|".join([
        "v2",
        device_id,
        client_id,
        client_mode,
        role,
        scopes,
        str(signed_at_ms),
        token,
        nonce,
    ])


def _sign_payload(payload: str, private_key_pem: str) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    signature = private_key.sign(payload.encode())
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _public_key_raw_base64(public_key_pem: str) -> str:
    pub = serialization.load_pem_public_key(public_key_pem.encode())
    raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _extract_openclaw_text(data: Any) -> str:
    try:
        output = data.get("output") if isinstance(data, dict) else None
        if not isinstance(output, list):
            return ""

        texts: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                t = c.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())

        return "\n".join(texts).strip()
    except Exception:
        return ""


def _extract_chat_completions_text(data: Any) -> str:
    try:
        if not isinstance(data, dict):
            return ""
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(msg, dict):
            return ""
        content = msg.get("content")
        return content.strip() if isinstance(content, str) else ""
    except Exception:
        return ""


def _extract_legacy_chat_text(data: Any) -> str:
    try:
        if not isinstance(data, dict):
            return ""
        # common legacy formats
        for k in ("response", "reply", "text", "message"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""
    except Exception:
        return ""


async def _probe_openclaw() -> bool:
    try:
        import websockets

        async with websockets.connect(OPENCLAW_WS_URL, open_timeout=5) as ws:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(raw)
                if isinstance(msg, dict) and msg.get("type") == "event" and msg.get("event") == "connect.challenge":
                    return True
            except Exception:
                return True
            return True
    except Exception:
        return False


class _OpenClawWsClient:
    def __init__(self):
        self._ws = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._identity: DeviceIdentity | None = None
        self._token = OPENCLAW_GATEWAY_TOKEN

    def _candidate_urls(self) -> List[str]:
        base = OPENCLAW_WS_URL.rstrip("/")
        # Some gateways expose WS on /ws rather than root.
        return [
            base,
            f"{base}/ws",
        ]

    @property
    def connected(self) -> bool:
        return bool(self._connected)

    async def connect(self) -> bool:
        async with self._lock:
            return await self._ensure_connected()

    async def _ensure_connected(self) -> bool:
        import websockets

        if self._ws is not None and self._connected:
            return True

        self._connected = False

        # Load device identity and token
        if not self._identity:
            self._identity = _load_device_identity()
        if not self._token:
            raise RuntimeError("OPENCLAW_GATEWAY_TOKEN not set")

        last_err: Exception | None = None
        for url in self._candidate_urls():
            try:
                self._ws = await websockets.connect(url, open_timeout=10)
                await self._auth_handshake()
                break
            except Exception as e:
                last_err = e
                try:
                    if self._ws is not None:
                        await self._ws.close()
                except Exception:
                    pass
                self._ws = None

        if self._ws is None:
            raise RuntimeError(f"OpenClaw WS connect failed for {self._candidate_urls()}: {last_err}")

        self._connected = True
        return True

    def _load_device_identity(self, path: str = "~/.openclaw/identity/device.json") -> Any:
        from dataclasses import dataclass
        @dataclass
        class DeviceIdentity:
            device_id: str
            public_key_pem: str
            private_key_pem: str

        expanded = os.path.expanduser(path)
        try:
            with open(expanded, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError as exc:
            raise RuntimeError("Device identity missing. Approve a device first with openclaw devices.") from exc
        return DeviceIdentity(
            device_id=data["deviceId"],
            public_key_pem=data["publicKeyPem"],
            private_key_pem=data["privateKeyPem"],
        )

    def _build_device_auth_payload(self, *, device_id: str, client_id: str, client_mode: str,
                                  role: str, scopes: str, signed_at_ms: int,
                                  token: str, nonce: str) -> str:
        return "|".join([
            "v2",
            device_id,
            client_id,
            client_mode,
            role,
            scopes,
            str(signed_at_ms),
            token,
            nonce,
        ])

    def _sign_payload(self, payload: str, private_key_pem: str) -> str:
        private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        signature = private_key.sign(payload.encode())
        return base64.urlsafe_b64encode(signature).decode().rstrip("=")

    def _public_key_raw_base64(self, public_key_pem: str) -> str:
        pub = serialization.load_pem_public_key(public_key_pem.encode())
        raw = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    async def _auth_handshake(self):
        if not self._ws or not self._identity:
            raise RuntimeError("WebSocket or identity not initialized")

        challenge = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=10))
        if challenge.get("event") != "connect.challenge":
            raise RuntimeError("Expected connect.challenge")
        nonce = challenge["payload"]["nonce"]
        signed_at = int(time.time() * 1000)
        role = "operator"
        scopes_list = ["operator.admin"]
        scopes = ",".join(scopes_list)
        payload = self._build_device_auth_payload(
            device_id=self._identity.device_id,
            client_id="gateway-client",
            client_mode="backend",
            role=role,
            scopes=scopes,
            signed_at_ms=signed_at,
            token=self._token,
            nonce=nonce,
        )
        signature = self._sign_payload(payload, self._identity.private_key_pem)
        req_id = str(uuid.uuid4())
        await self._ws.send(json.dumps({
            "type": "req",
            "id": req_id,
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "gateway-client",
                    "displayName": "Infinity Backend",
                    "version": "1.0.0",
                    "platform": sys.platform,
                    "mode": "backend",
                },
                "caps": [],
                "auth": {"token": self._token},
                "role": role,
                "scopes": scopes_list,
                "device": {
                    "id": self._identity.device_id,
                    "publicKey": _public_key_raw_base64(self._identity.public_key_pem),
                    "signature": signature,
                    "signedAt": signed_at,
                    "nonce": nonce,
                },
            },
        }))

        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
            resp = json.loads(raw)
            if isinstance(resp, dict) and resp.get("type") == "res" and resp.get("id") == req_id:
                if not resp.get("ok"):
                    raise RuntimeError(f"OpenClaw handshake failed: {resp}")
                break

    async def disconnect(self):
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._connected = False

    async def send_text(self, *, session_id: str, text: str, timeout_s: float = 60.0) -> str:
        if not session_id:
            session_id = "default"
        session_key = f"agent:main:infinity_{session_id}"

        async with self._lock:
            await self._ensure_connected()

            req_id = str(uuid.uuid4())
            await self._ws.send(json.dumps({
                "type": "req",
                "id": req_id,
                "method": "chat.send",
                "params": {
                    "sessionKey": session_key,
                    "message": text,
                    "deliver": False,
                    "idempotencyKey": uuid.uuid4().hex,
                },
            }))

            end_at = asyncio.get_event_loop().time() + timeout_s
            while True:
                remaining = max(0.1, end_at - asyncio.get_event_loop().time())
                raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
                msg = json.loads(raw)
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "event" or msg.get("event") != "chat":
                    continue
                payload = msg.get("payload")
                if not isinstance(payload, dict):
                    continue
                if payload.get("sessionKey") != session_key:
                    continue
                state = payload.get("state")
                if state == "streaming":
                    # Optional: you could collect streaming chunks here if needed
                    continue
                if state != "final":
                    continue
                message = payload.get("message")
                if not isinstance(message, dict):
                    return "(No response)"
                content = message.get("content")
                if not isinstance(content, list) or not content:
                    return "(No response)"
                first = content[0]
                if not isinstance(first, dict):
                    return "(No response)"
                t = first.get("text")
                if isinstance(t, str) and t.strip():
                    return t.strip()
                return "(No response)"


openclaw_ws_client = _OpenClawWsClient()


# ----------------------------------------------------------------------------------
# OpenCode HTTP Client — manages opencode serve sidecar + session-per-conversation
# ----------------------------------------------------------------------------------

class OpenCodeClient:
    """
    Manages a persistent opencode server (opencode serve) and maps
    neurocomputer conversation IDs to opencode session IDs.

    Usage:
        client = OpenCodeClient()
        await client.ensure_server()
        text = await client.send(cid="abc123", task="refactor this fn",
                                  stream_callback=my_callback)
    """

    def __init__(self, base_url: str = OPENCODE_SERVER_URL):
        self._base_url = base_url
        self._proc: Optional[asyncio.subprocess.Process] = None
        # Maps neurocomputer cid → opencode session id
        self._sessions: Dict[str, str] = {}

    # ── server lifecycle ──────────────────────────────────────────────

    async def ensure_server(self) -> bool:
        """Ping the server; start opencode serve if it's not already running."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{self._base_url}/global/health", timeout=aiohttp.ClientTimeout(total=2)) as r:
                    if r.status == 200:
                        return True
        except Exception:
            pass

        # Start opencode serve
        logger.info("[OpenCode] Starting opencode serve...")
        try:
            self._proc = await asyncio.create_subprocess_exec(
                "opencode", "serve", "--port", str(self._server_port()),
                "--hostname", "127.0.0.1",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            # Wait up to 8 s for it to come up
            for _ in range(16):
                await asyncio.sleep(0.5)
                try:
                    import aiohttp as _ah
                    async with _ah.ClientSession() as s:
                        async with s.get(f"{self._base_url}/global/health", timeout=_ah.ClientTimeout(total=1)) as r:
                            if r.status == 200:
                                logger.info("[OpenCode] Server ready")
                                return True
                except Exception:
                    pass
            logger.warning("[OpenCode] Server did not become ready in time")
            return False
        except Exception as e:
            logger.error(f"[OpenCode] Failed to start server: {e}")
            return False

    def _server_port(self) -> int:
        try:
            return int(self._base_url.split(":")[-1])
        except Exception:
            return 14096

    async def stop_server(self):
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            await self._proc.wait()
            self._proc = None

    # ── session management ────────────────────────────────────────────

    async def _get_or_create_session(self, cid: str) -> str:
        """Return existing opencode session for this cid, or create a new one."""
        if cid in self._sessions:
            return self._sessions[cid]
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{self._base_url}/session",
                json={"title": f"neuro-{cid[:8]}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                data = await r.json()
        session_id = data["id"]
        self._sessions[cid] = session_id
        logger.info(f"[OpenCode] Created session {session_id} for cid {cid}")
        return session_id

    # ── message send + SSE streaming ─────────────────────────────────

    async def send(
        self,
        cid: str,
        task: str,
        stream_callback=None,
        timeout: float = 120.0,
    ) -> str:
        """
        Send a message to OpenCode and return the final assistant text.
        If stream_callback is provided, calls it with each text delta chunk.
        """
        import aiohttp

        await self.ensure_server()
        session_id = await self._get_or_create_session(cid)

        url = f"{self._base_url}/session/{session_id}/message"
        payload = {
            "parts": [{"type": "text", "text": task}],
        }

        accumulated = []

        async with aiohttp.ClientSession() as s:
            async with s.post(
                url,
                json=payload,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                # Read SSE stream
                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    etype = event.get("type", "")
                    props = event.get("properties", {})

                    # Streaming text delta
                    if etype == "message.part.delta":
                        delta = props.get("delta", "")
                        if delta and props.get("field") == "text":
                            accumulated.append(delta)
                            if stream_callback:
                                await stream_callback(delta)

                    # Full part update (catches final text if no deltas)
                    elif etype == "message.part.updated":
                        part = props.get("part", {})
                        if part.get("type") == "text":
                            # Replace accumulated with the authoritative full text
                            full = part.get("text", "")
                            if full:
                                accumulated = [full]

                    # Session done
                    elif etype in ("session.idle", "session.turn.close"):
                        break

                    # Surface errors
                    elif etype == "session.error":
                        err = props.get("error", {})
                        raise RuntimeError(f"OpenCode error: {err.get('data', {}).get('message', str(err))}")

        return "".join(accumulated) or "(no response)"


opencode_client = OpenCodeClient()


# ----------------------------------------------------------------------------------
# Claude CLI WebSocket Bridge - Proxies to claude_chat.py server (default: localhost:9593)
# ----------------------------------------------------------------------------------

CLAUDE_WS_URL = "ws://localhost:9593"

@app.websocket("/ws/claude")
async def claude_websocket(ws: WebSocket):
    """WebSocket bridge to Claude CLI WebSocket server."""
    await ws.accept()
    logger.info("Claude WebSocket connected (/ws/claude)")

    try:
        # Connect to Claude CLI server
        async with websockets.connect(CLAUDE_WS_URL) as claude_ws:
            # Receive welcome message
            welcome = await claude_ws.recv()
            await ws.send_text(welcome)

            # Bidirectional proxy
            async def proxy_to_claude():
                async for msg in ws:
                    await claude_ws.send(msg)

            async def proxy_to_client():
                async for msg in claude_ws:
                    await ws.send_text(msg)

            await asyncio.gather(proxy_to_claude(), proxy_to_client())

    except websockets.exceptions.ConnectionClosed:
        logger.info("Claude WebSocket disconnected")
    except Exception as e:
        logger.error(f"Claude WebSocket error: {e}")


# ----------------------------------------------------------------------------------
# OpenClaw Control API - Proxies to OpenClaw gateway (default: 127.0.0.1:18789)
# ----------------------------------------------------------------------------------


@app.post("/openclaw/connect")
async def openclaw_connect():
    """Mark OpenClaw as connected if the gateway is reachable."""
    try:
        ok = await openclaw_ws_client.connect()
        openclaw_state["connected"] = bool(ok)
        openclaw_state["last_error"] = ""
        return {"success": True, **openclaw_state}
    except Exception as e:
        openclaw_state["connected"] = False
        openclaw_state["last_error"] = str(e)
        return {"success": False, **openclaw_state}


@app.post("/openclaw/disconnect")
async def openclaw_disconnect():
    try:
        await openclaw_ws_client.disconnect()
    except Exception:
        pass
    openclaw_state["connected"] = False
    return {"success": True, **openclaw_state}


@app.get("/openclaw/state")
async def openclaw_get_state():
    return openclaw_state


@app.post("/openclaw/send")
async def openclaw_send(body: dict):
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    # Session strategy: accept optional session_id/cid, otherwise default.
    session_id = body.get("session_id") or body.get("cid") or "default"

    try:
        response_text = await openclaw_ws_client.send_text(session_id=str(session_id), text=str(text))
        openclaw_state["connected"] = True
        openclaw_state["last_response"] = response_text
        openclaw_state["last_error"] = ""
        return {"response": response_text}
    except Exception as e:
        openclaw_state["connected"] = False
        openclaw_state["last_error"] = str(e)
        return {"error": str(e)}


@app.websocket("/ws/openclaw/state")
async def openclaw_websocket(ws: WebSocket):
    """WebSocket for OpenClaw connection state updates."""
    await ws.accept()
    logger.info("OpenClaw WebSocket connected (/ws/openclaw/state)")

    last_state: Dict[str, Any] = {}

    try:
        while True:
            # OpenClaw global poller updates the state asynchronously
            state = dict(openclaw_state)
            if state != last_state:
                await ws.send_json({"type": "state", **state})
                last_state = state
            else:
                await ws.send_json({"type": "heartbeat"})

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("OpenClaw WebSocket disconnected")
    except Exception as e:
        logger.error(f"OpenClaw WebSocket error: {e}")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Simple home page with usage instructions"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Neuro Server</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                max-width: 900px; 
                margin: 0 auto; 
                padding: 30px; 
                background-color: #0f172a;
                color: #e2e8f0; 
            }
            h1, h2, h3 { 
                color: #f1f5f9; 
                border-bottom: 1px solid #334155;
                padding-bottom: 10px;
            }
            h1 { 
                font-size: 2.5em; 
                background: linear-gradient(to right, #4f46e5, #10b981);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 40px;
            }
            .section {
                background-color: rgba(30, 41, 59, 0.8);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .endpoints {
                display: grid;
                grid-template-columns: 1fr;
                gap: 20px;
            }
            .endpoint { 
                background-color: rgba(15, 23, 42, 0.8);
                border-radius: 8px;
                padding: 15px; 
                margin-bottom: 15px; 
                border-left: 4px solid #4f46e5;
            }
            pre { 
                background-color: #1e293b; 
                padding: 12px; 
                border-radius: 5px; 
                overflow: auto;
                color: #94a3b8;
            }
            code {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 0.9em;
            }
            .tag {
                display: inline-block;
                padding: 2px 8px;
                margin-right: 5px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
            }
            .tag.get {
                background-color: #3b82f6;
                color: white;
            }
            .tag.post {
                background-color: #22c55e;
                color: white;
            }
            .tag.ws {
                background-color: #8b5cf6;
                color: white;
            }
        </style>
    </head>
    <body>
        <h1>Neuro Server</h1>
        
        <div class="section">
            <h2>Overview</h2>
            <p>This server provides chat and brain functionalities for the Neuro.</p>
        </div>
        
        <div class="section">
            <h2>API Endpoints</h2>
            <div class="endpoints">
                <div>
                    <h3>Neuro Server</h3>
                    <div class="endpoint">
                        <span class="tag post">POST</span> <code>/chat</code>
                        <p>Send a chat message to the Neuro brain</p>
                        <p><strong>Body:</strong></p>
                        <pre>{
  "cid": "conversation_id", // optional
  "text": "Your message here"
}</pre>
                    </div>
                    
                    <div class="endpoint">
                        <span class="tag ws">WS</span> <code>/ws/{cid}</code>
                        <p>WebSocket connection for real-time updates</p>
                        <p>Connect to this endpoint to receive events from the Neuro brain.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Using with CLI Client</h2>
            <p>Run the <code>cli_client.py</code> script to connect to this server:</p>
            <pre>python cli_client.py --host localhost --port 7000</pre>
        </div>
    </body>
    </html>
    """

# ----------------------------------------------------------------------------------
# Window Management API (for mobile remote control)
# ----------------------------------------------------------------------------------

import subprocess
import io
import struct

@app.get("/windows")
async def list_windows():
    """List all open windows grouped by application class."""
    try:
        # Get all visible windows with their IDs
        result = subprocess.run(
            ['xdotool', 'search', '--onlyvisible', ''],
            capture_output=True, text=True, timeout=5
        )
        window_ids = result.stdout.strip().split('\n')
        
        windows = []
        apps = {}
        
        for wid in window_ids:
            wid = wid.strip()
            if not wid:
                continue
            
            # Get window name
            try:
                name_result = subprocess.run(
                    ['xdotool', 'getwindowname', wid],
                    capture_output=True, text=True, timeout=2
                )
                name = name_result.stdout.strip()
            except:
                name = ""
            
            # Get window class
            try:
                class_result = subprocess.run(
                    ['xprop', '-id', wid, 'WM_CLASS'],
                    capture_output=True, text=True, timeout=2
                )
                class_line = class_result.stdout.strip()
                if 'WM_CLASS' in class_line:
                    classes = class_line.split('"')
                    if len(classes) >= 4:
                        app_class = classes[3].lower()
                        display_class = classes[1]
                    else:
                        app_class = display_class = "unknown"
                else:
                    app_class = display_class = "unknown"
            except:
                app_class = display_class = "unknown"
            
            if not name:
                continue
                
            window_info = {
                "id": wid,
                "title": name,
                "class": app_class,
                "windowClass": app_class,
                "display_class": display_class,
                "displayClass": display_class
            }
            windows.append(window_info)
            
            # Group by app class
            if app_class not in apps:
                apps[app_class] = {
                    "class": app_class,
                    "windowClass": app_class,
                    "display_class": display_class,
                    "displayClass": display_class,
                    "windows": []
                }
            apps[app_class]["windows"].append(window_info)
        
        return {
            "windows": windows,
            "apps": list(apps.values())
        }
    except Exception as e:
        logger.error(f"Error listing windows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/windows/{window_id}/screenshot")
async def window_screenshot(window_id: str):
    """Get screenshot of a specific window as PNG."""
    try:
        # Use xwd to capture the window, then convert to PNG
        xwd_path = f"/tmp/window_{window_id}.xwd"
        png_path = f"/tmp/window_{window_id}.png"
        
        # Capture window with xwd
        result = subprocess.run(
            ['xwd', '-id', window_id, '-silent'],
            capture_output=True, timeout=10
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=404, detail="Window not found or not accessible")
        
        # Write xwd data
        with open(xwd_path, 'wb') as f:
            f.write(result.stdout)
        
        # Convert to PNG using ImageMagick
        convert_result = subprocess.run(
            ['convert', xwd_path, png_path],
            capture_output=True, timeout=10
        )
        
        if convert_result.returncode != 0:
            # If convert fails, try returning raw xwd
            import base64
            return JSONResponse({
                "error": "convert failed",
                "xwd_base64": base64.b64encode(result.stdout).decode()
            })
        
        # Read PNG and return as base64
        with open(png_path, 'rb') as f:
            import base64
            png_data = base64.b64encode(f.read()).decode()
        
        # Cleanup
        try:
            os.remove(xwd_path)
            os.remove(png_path)
        except:
            pass
        
        return {"screenshot": png_data, "window_id": window_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error capturing window screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/windows/{window_id}/focus")
async def focus_window(window_id: str):
    """Focus/activate a specific window."""
    try:
        result = subprocess.run(
            ['xdotool', 'windowactivate', '--sync', window_id],
            capture_output=True, timeout=5
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=404, detail="Window not found")
        
        return {"success": True, "window_id": window_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error focusing window: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/windows/{window_id}/click")
async def click_window(window_id: str, x: int = None, y: int = None):
    """Click on a specific position in a window."""
    try:
        if x is not None and y is not None:
            result = subprocess.run(
                ['xdotool', 'windowfocus', window_id, 'mouseclick', '--window', window_id, '1'],
                capture_output=True, timeout=5
            )
        else:
            result = subprocess.run(
                ['xdotool', 'windowactivate', '--sync', window_id, 'click', '1'],
                capture_output=True, timeout=5
            )
        
        if result.returncode != 0:
            raise HTTPException(status_code=404, detail="Window not found or click failed")
        
        return {"success": True, "window_id": window_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clicking window: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7000)),
        reload=False,
    )
