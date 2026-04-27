# S3 — Multi-Agent Meeting Rooms (Refresh)

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT (refresh of existing draft `docs/AGENT_MEETING_ROOMS.md`)
**Depends on:** S6 (abstract talk primitive)
**Blocks:** none
**ETA:** 90+ minutes (largest single piece — ship last)

---

## Goal

Make the existing **DRAFT** `AGENT_MEETING_ROOMS.md` **executable** by reusing the substrates we now have (S2 defaults, S6 talk primitive). A "Meeting Room" is an isolated collaboration space where 2+ agents work together via:

- **Text channel** — shared transcript, persisted in DB.
- **Voice channel** — LiveKit room with multiple participants (existing infra).
- **Shared room state** — KV store of context, files, task queue (a blackboard sub-namespace).
- **Per-agent message routing** — agents only see relevant messages.
- **Turn-taking** — managed by a "room brain" mediator neuro.

This spec **refreshes** the DRAFT by removing speculative parts, mapping concepts onto the talk primitive, and producing a checklist that ships.

---

## What changes vs. the DRAFT

The original DRAFT (`docs/AGENT_MEETING_ROOMS.md`) was written before S2/S6 existed. Updates:

| DRAFT element | This spec |
|---|---|
| "Mediator neuro merges responses" | Mediator uses `agent.talk(target, msg)` from S6 — no custom merging logic |
| "Room state in custom PubSub" | Reuse existing `core/pubsub.py` (`hub`) with `room_id`-prefixed channels |
| "Celery for persistence + asyncio for real-time" | All asyncio for v1; Celery only if a multi-process need arises |
| "Per-room shared KV" | A `rooms/<room_id>/` sub-tree on the existing blackboard |

---

## Core data model

```python
@dataclass
class Room:
    room_id: str
    name: str
    agents: list[str]                  # agent_ids participating
    voice_room_id: str | None = None   # LiveKit room id, optional
    blackboard_path: str = "rooms/{room_id}/"
    transcript: list[dict] = field(default_factory=list)  # ordered messages
    created_at: str = ""               # ISO 8601
    state: dict = field(default_factory=dict)  # shared KV
    turn_policy: str = "round_robin"   # 'round_robin' | 'mediator' | 'free'
    max_turns: int = 20                # safety cap
```

Persistence: a SQLite table `rooms` (id, name, agents_json, transcript_json, state_json, voice_room_id, created_at, status) — rebuild Room dataclasses on read.

---

## Mediator neuro — `room_mediator`

The mediator's job is **turn-taking**, not response-merging. It:

1. Reads the latest message in the transcript.
2. Decides who speaks next based on `turn_policy`:
   - `round_robin` — next agent in the list.
   - `mediator` — LLM picks which agent has the most relevant role.
   - `free` — broadcast to all (parallel `agent.talk` calls, results appended in order).
3. Calls `agent.talk(next_agent, latest_message)`.
4. Appends the reply to the transcript.
5. Re-evaluates: continue, hand to next agent, or terminate (if `[room: done]` token in reply or `len(transcript) >= max_turns`).

The mediator itself is a regular neuro that lives in any profile. It does not need to be in the room as a "participant" — it operates on the room from outside.

---

## Voice channel

LiveKit infrastructure already exists (`livekit.service`, `livekit.yaml.example`, `core/voice_manager.py`). For a room with `voice_room_id != None`:

- The room creates a LiveKit room via existing manager.
- Each agent that has a voice surface (TTS) joins the LiveKit room when speaking.
- The mediator routes turn-taking by token order on text; voice is a passive surface (TTS reads each new transcript line).
- Users in the LiveKit room hear the conversation in real time.

This spec does **not** add bidirectional STT inside the room — that's a future iteration.

---

## Files to add / edit

### New

- `neurocomputer/core/rooms.py` — `Room` dataclass + `RoomManager` (CRUD, persistence).
- `neurocomputer/core/rooms_db.py` — SQLite wrapper for the `rooms` table.
- `neurocomputer/neuros/room_create/{conf.json, code.py}` — creates a new room.
- `neurocomputer/neuros/room_post/{conf.json, code.py}` — posts a message to a room (kicks the mediator).
- `neurocomputer/neuros/room_close/{conf.json, code.py}` — terminates a room.
- `neurocomputer/neuros/room_mediator/{conf.json, code.py, prompt.txt}` — orchestrates turn-taking.
- `neuro_web/components/rooms/RoomPanel.tsx` — minimal room view (transcript + participants + voice toggle). ~150 LoC.

### Edit

- `neurocomputer/server.py` — endpoints `GET /api/rooms`, `POST /api/rooms`, `GET /api/rooms/{id}`, `DELETE /api/rooms/{id}`, `POST /api/rooms/{id}/messages`.
- `neurocomputer/profiles/general.json` and `neurolang_dev.json` — include `room_*` neuros.

---

## Implementation Checklist

- [ ] **3.1** Create `core/rooms_db.py` (DDL + insert/update/delete/list).
- [ ] **3.2** Create `core/rooms.py` (`Room` dataclass + `RoomManager` singleton).
- [ ] **3.3** Create `neuros/room_create/` (creates a Room, persists, returns `room_id`).
- [ ] **3.4** Create `neuros/room_post/` (appends message to transcript, calls `room_mediator` for next turn).
- [ ] **3.5** Create `neuros/room_close/` (sets room status to closed; voice room torn down via existing manager).
- [ ] **3.6** Create `neuros/room_mediator/` — implements the round-robin logic first; mediator-LLM and free policies as follow-ups.
- [ ] **3.7** Add HTTP endpoints to `server.py`.
- [ ] **3.8** Create `RoomPanel.tsx` — participants chips, transcript list, message input, "Toggle Voice" button.
- [ ] **3.9** Add `room_*` neuros to relevant profiles.
- [ ] **3.10** Test: create a room with `agents=["neuro", "nl_dev"]`, post "explain how the email stdlib works", verify both agents reply in turn.
- [ ] **3.11** Test: voice — create a room with voice enabled, verify TTS plays each turn.
- [ ] **3.12** Mark spec `Status: SHIPPED`.

---

## Acceptance criteria

1. **Two-agent text room.** Posting a message to a room with two agents produces alternating replies in the transcript.
2. **Persistence.** Room survives server restart; transcript is intact.
3. **Termination.** Posting `[room: done]` or hitting `max_turns` ends the room cleanly.
4. **Voice (basic).** When `voice_room_id` is set, each new transcript line is read aloud via TTS in the LiveKit room.
5. **Cancellation.** `DELETE /api/rooms/{id}` stops any in-flight mediator turn within ~5s.

---

## Out of scope

- **Bidirectional voice with agents listening to user voice in real time** — keep the user as a text-only participant for now (or read user voice via existing transcription, which is already in place but routes through user's chat, not the room).
- **More than 4 agents per room** — supported in principle, but UI test only covers 2–3.
- **Cross-agency rooms** — defer; rooms must contain agents in the same agency this round.
- **Persistent room files / artifacts** — use the blackboard sub-path manually for now.

---

## Open questions

- **Should the mediator itself be a "room participant" with a visible turn?** Recommend: NO — mediator is metadata layer, not a speaker. Saves user confusion.
- **Should turn-taking use a DAG (next-speaker-by-role) instead of round-robin?** Round-robin v1; DAG/role-based in a follow-up if `turn_policy="mediator"` proves necessary.

---

## Notes for the executing agent

- The DRAFT in `docs/AGENT_MEETING_ROOMS.md` has more elaborate ideas (Claude Code Infinity wrapper, Celery, custom PubSub) — **do NOT implement them this round**. They are future work. Stay strictly within this spec.
- The **mediator is the load-bearing piece**. Once the round-robin mediator works for two agents, the rest is shape.
- Reuse `core/pubsub.py` for any room event publishing — do not add a second pubsub.
- Voice integration: extend the existing `voice_manager` rather than starting a new manager.
