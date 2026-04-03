#!/usr/bin/env python3
import asyncio
import base64
import json
import logging
import os
import sys
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
    llm = OpenAI()

    system_prompt = """Extract job data from Upwork posting. Return JSON:
{"title": "...", "company": "...", "budget": "...", "skills": [...], "description": "...", "verdict": "worth_apply|skip|maybe", "red_flags": [...]}
If not found use null."""

    try:
        response = llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text[:8000]}
            ],
            temperature=0.3
        )
        job_data = json.loads(response.choices[0].message.content)
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

        # Save audio_url back to the conversation message if msg_id is a numeric index
        if msg_id.isdigit():
            try:
                conv = Conversation(cid)
                idx = int(msg_id)
                if 0 <= idx < len(conv._log):
                    conv._log[idx]["audio_url"] = audio_url
                    conv._log[idx]["is_voice"] = True
                    conv._save()
                    logger.info(f"[TTS] Saved audio_url to conversation {cid} msg {idx}")
            except Exception as e:
                logger.warning(f"[TTS] Could not update conversation msg: {e}")

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
        logger.info(f"Processing message from {cid} with agent {agent.agent_id}: {text}")
        reply = await agent.handle_message(cid, text, agent_id=agent.agent_id)
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
async def list_conversations(agent_id: str = None):
    """List all conversations, optionally filtered by agent_id"""
    conv_dir = Path(__file__).parent / "conversations"
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
                    else:
                        messages = data.get("messages", [])
                        conv_agent_id = data.get("agent_id")

                    # Filter by agent_id if provided
                    if agent_id and conv_agent_id != agent_id:
                        continue

                    if messages:
                        # Get title from stored title or first message
                        title = data.get("title", "New Chat")
                        if title == "New Chat":
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
                            "agentId": conv_agent_id
                        })
            except Exception:
                pass
    # Sort by updatedAt
    conversations.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return conversations

@app.get("/conversation/{cid}")
async def get_conversation(cid: str):
    """Get a specific conversation"""
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if conv_file.exists():
        with open(conv_file) as fp:
            data = json.load(fp)
            # Handle both old format (array) and new format (object)
            if isinstance(data, list):
                messages = data
                agent_id = None
            else:
                messages = data.get("messages", [])
                agent_id = data.get("agent_id")

            # Convert to frontend format
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
            return {"id": cid, "agentId": agent_id, "messages": formatted}
    return {"id": cid, "agentId": None, "messages": []}

@app.post("/conversation")
async def create_conversation(body: dict = None):
    """Create a new conversation"""
    cid = uuid.uuid4().hex
    agent_id = None
    if body:
        agent_id = body.get("agent_id")
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    with open(conv_file, "w") as fp:
        json.dump({"agent_id": agent_id, "messages": [], "title": "New Chat"}, fp)
    return {"id": cid, "cid": cid, "title": "New Chat", "agentId": agent_id}

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
        
        with open(conv_file, "w") as fp:
            json.dump(data, fp, indent=2)
        
        return {"success": True, "conversation": data}
    return {"success": False, "error": "Conversation not found"}

@app.delete("/conversation/{cid}")
async def delete_conversation(cid: str):
    """Delete a conversation"""
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if conv_file.exists():
        conv_file.unlink()
        return {"success": True}
    return {"success": False, "error": "Conversation not found"}


# ----------------------------------------------------------------------------------
# Voice API Endpoints (LiveKit)
# ----------------------------------------------------------------------------------

@app.post("/voice/token")
async def voice_token(body: dict):
    """
    Create a voice session and return token for client to join.
    
    Body:
        {"user_id": "optional_user_id"}
    
    Returns:
        {"token": "...", "room_name": "...", "url": "wss://..."}
    """
    user_id = body.get("user_id") or uuid.uuid4().hex[:8]
    
    try:
        result = await voice_manager.create_session(user_id)
        logger.info(f"Voice session created for {user_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create voice session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create voice session: {e}")


@app.post("/voice/end")
async def voice_end(body: dict):
    """
    End a voice session.
    
    Body:
        {"user_id": "..."}
    """
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    await voice_manager.end_session(user_id)
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
        room_name = f"voice-{user_id}"
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
    
    room_name = f"voice-{user_id}"
    
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

        # Move mouse to center of new monitor using absolute coordinates
        center_x = monitor['left'] + monitor['width'] // 2
        center_y = monitor['top'] + monitor['height'] // 2
        try:
            # Use absolute coordinates - --screen flag doesn't work reliably on this system
            subprocess.run(["xdotool", "mousemove", str(center_x), str(center_y)], check=False)
            logger.info(f"[Display] Moved mouse to center of monitor {_current_display_index}")
        except Exception as e:
            logger.warning(f"[Display] Failed to move mouse: {e}")

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
        
        # Save voice message to conversation file (legacy)
        try:
            conv = Conversation(cid)
            conv.add("user", transcription, audio_url=audio_url, is_voice=True)
            logger.info(f"[VoiceMsg] Saved voice to conversation {cid}: {transcription[:30]}... audio={audio_url}")
        except Exception as e:
            logger.error(f"[VoiceMsg] Could not save voice to conversation file: {e}")

        # Get or create chat room and send voice message
        try:
            chat_room = await chat_manager.get_or_create_room(cid, agent_id or "neuro")
            
            # Ensure agent is started before sending
            if not chat_room._agent_started:
                logger.info(f"[VoiceMsg] Starting agent for voice message room: {cid}")
                await chat_room.start_agent()
                # Wait for agent to connect
                import asyncio
                await asyncio.sleep(1)
            
            # Send voice message to chat room
            from core.chat_handler import ChatMessage
            voice_msg = ChatMessage(
                msg_type="voice",
                sender="user",
                content=transcription,
                message_id=message_id,
                audio_url=audio_url,
                origin=origin,
            )
            await chat_room.send_to_all(voice_msg, topic="chat_message")
            logger.info(f"[VoiceMsg] Sent voice message via LiveKit DataChannel")
        except Exception as e:
            logger.warning(f"[VoiceMsg] Could not send via LiveKit: {e}")
            # Fallback to old hub queue
            await hub.queue(cid).put({
                "topic": "user_voice", 
                "data": {
                    "text": transcription,
                    "audio_url": audio_url,
                    "message_id": message_id
                }
            })

        # Trigger the Neuro agent to process the transcription
        # Use chat_manager's brain for response via LiveKit
        if bt:
            bt.add_task(_handle_voice_message, cid, transcription, agent_id, origin)
        else:
            asyncio.create_task(_handle_voice_message(cid, transcription, agent_id, origin))
        
        logger.info(f"[VoiceMsg] Complete: {transcription[:50]}...")
        
        return {
            "message_id": message_id,
            "transcription": transcription,
            "audio_url": audio_url,
        }
        
    except Exception as e:
        logger.error(f"[VoiceMsg] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_voice_message(cid: str, transcription: str, agent_id: str = None, origin: str = None):
    """Handle voice message by sending to ChatRoom handler which processes via LiveKit only.
    
    This avoids duplicate TTS by suppressing hub publish (WebSocket).
    """
    try:
        # Get or create chat room and ensure agent is started
        chat_room = await chat_manager.get_or_create_room(cid, agent_id or "neuro")
        
        if not chat_room._agent_started:
            logger.info(f"[VoiceMsg] Starting agent for voice message room: {cid}")
            await chat_room.start_agent()
            # Wait for agent to connect
            import asyncio
            await asyncio.sleep(1)
        
        # Suppress hub publish for this brain instance to avoid duplicate TTS
        if chat_room._brain:
            chat_room._brain._suppress_hub = True
        
        # Create a ChatMessage and process through the chat handler
        from core.chat_handler import ChatMessage
        voice_msg = ChatMessage(
            msg_type="voice",
            sender="user",
            content=transcription,
            origin=origin,
        )
        
        # Process through the chat room's handler (which calls brain.handle() but sends via LiveKit only)
        await chat_room.handle_user_message(voice_msg)
        logger.info(f"[VoiceMsg] Voice message processed via ChatRoom handler")
        
        # Re-enable hub publish
        if chat_room._brain:
            chat_room._brain._suppress_hub = False
        
    except Exception as e:
        logger.error(f"[VoiceMsg] Error handling voice message: {e}")
        # Make sure to re-enable hub publish on error too
        try:
            chat_room = await chat_manager.get_room(cid)
            if chat_room and chat_room._brain:
                chat_room._brain._suppress_hub = False
        except:
            pass


@app.post("/voice-type")
async def voice_type(
    file: UploadFile = File(...),
    press_enter: bool = False,
):
    """
    Voice-to-Type: Transcribe audio and type the text at the current cursor position.
    Uses xdotool to simulate keyboard input on the desktop.
    If press_enter is True, presses Enter after typing.
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

        # Transcribe using Whisper
        logger.info("[VoiceType] Transcribing...")
        transcription = await transcribe_audio(str(audio_path))

        if not transcription.strip():
            return {"transcription": "", "typed": False}

        # Type the text at the current cursor position using xdotool
        logger.info(f"[VoiceType] Typing: {transcription[:80]}...")
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "12", transcription],
            check=False, capture_output=True, timeout=10
        )

        # Optionally press Enter after typing
        if press_enter:
            logger.info("[VoiceType] Pressing Enter")
            subprocess.run(
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
# Windsurf Control API - Proxies to TS server on port 9333
# ----------------------------------------------------------------------------------

import httpx
import uuid
import sys
import os

WINDSURF_TS_SERVER = "http://localhost:9333"

# Global HTTP client to prevent port exhaustion (TIME_WAIT socket leaks)
_httpx_client = None

def get_httpx_client():
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=60.0)
    return _httpx_client

openclaw_state: Dict[str, Any] = {
    "connected": False,
    "last_response": "",
    "last_error": "",
}

windsurf_state_global: Dict[str, Any] = {}

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    await db.init()
    logger.info("Starting background pollers...")
    asyncio.create_task(_global_windsurf_poller())
    asyncio.create_task(_global_openclaw_poller())

@app.on_event("shutdown")
async def shutdown_event():
    global _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
        _httpx_client = None

async def _global_windsurf_poller():
    global windsurf_state_global
    while True:
        try:
            state = await _proxy_windsurf("GET", "/state")
            windsurf_state_global = state
        except Exception:
            pass
        await asyncio.sleep(1)

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

async def _proxy_windsurf(method: str, path: str, body: dict = None) -> dict:
    """Proxy request to Windsurf TS server using a persistent client pool"""
    try:
        client = get_httpx_client()
        url = f"{WINDSURF_TS_SERVER}{path}"
        if method == "GET":
            r = await client.get(url)
        else:
            r = await client.post(url, json=body or {})
        return r.json()
    except httpx.ConnectError:
        return {"error": "Windsurf TS server not running. Start with: npx ts-node experiments/windsurf_automation/windsurf_server.ts"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/windsurf/connect")
async def windsurf_connect(body: dict = {}):
    """Connect to Windsurf IDE via CDP"""
    return await _proxy_windsurf("POST", "/connect", body)

@app.post("/windsurf/disconnect")
async def windsurf_disconnect():
    """Disconnect from Windsurf"""
    return await _proxy_windsurf("POST", "/disconnect")

@app.get("/windsurf/state")
async def windsurf_state():
    """Get current Windsurf state"""
    return await _proxy_windsurf("GET", "/state")

@app.post("/windsurf/send")
async def windsurf_send(body: dict):
    """Send a message to Windsurf"""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    return await _proxy_windsurf("POST", "/send", {"text": text})

@app.post("/windsurf/run")
async def windsurf_run():
    """Run the pending command in Windsurf"""
    return await _proxy_windsurf("POST", "/run")

@app.post("/windsurf/skip")
async def windsurf_skip():
    """Skip the pending command in Windsurf"""
    return await _proxy_windsurf("POST", "/skip")

@app.post("/windsurf/accept")
async def windsurf_accept():
    """Accept all pending file changes in Windsurf"""
    return await _proxy_windsurf("POST", "/accept")

@app.post("/windsurf/reject")
async def windsurf_reject():
    """Reject all pending file changes in Windsurf"""
    return await _proxy_windsurf("POST", "/reject")

# WebSocket for Windsurf state updates - polls TS server
# NOTE: cannot be /ws/windsurf because /ws/{cid} would capture it depending on route order.
@app.websocket("/ws/windsurf/state")
async def windsurf_websocket(ws: WebSocket):
    """WebSocket for real-time Windsurf state updates"""
    await ws.accept()
    logger.info("Windsurf WebSocket connected (/ws/windsurf/state)")
    
    last_state = {}
    
    try:
        while True:
            # Use globally polled state instead of fetching per-client
            state = dict(windsurf_state_global)
            
            # Only send if state changed
            if state != last_state:
                await ws.send_json({"type": "state", **state})
                last_state = state.copy()
            else:
                # Send heartbeat
                await ws.send_json({"type": "heartbeat"})
            
            await asyncio.sleep(1)  # Poll every second
    except WebSocketDisconnect:
        logger.info("Windsurf WebSocket disconnected")
    except Exception as e:
        logger.error(f"Windsurf WebSocket error: {e}")


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
# Main execution
# ----------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7000,
        reload=False,
    )
