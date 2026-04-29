# Voice Call Streaming + Low-Latency Pipeline — Design

**Date:** 2026-04-30
**Status:** Spec — pending user review
**Scope:** Replace batch-sequential voice pipeline with streaming pipeline; add smart turn detection and gated barge-in.

## Problem

The current LiveKit voice call has 3-7s latency from "user stops speaking" to "first audio plays". Conversations feel sluggish. The batch-sequential pipeline (VAD silence → Whisper batch STT → wait-for-task.done → batch OpenAI TTS) has every stage blocking on the previous one's full completion.

The repo already contains streaming-capable building blocks that are not wired:
- `sarvam_stt.py` — WebSocket streaming with interim results, unused
- `elevenlabs_tts.py` — streaming-capable TTS, unused
- `brain.py` — already publishes chunked assistant events to a hub queue, but the consumer (`InfinityBrainStream._run` in `voice_manager.py:188`) waits for `task.done` before forwarding to TTS

## Goals

- Median speech-end → first-audio latency **< 1.5 s**
- p95 < 2.5 s
- Natural conversation feel: smart turn detection, mid-response barge-in
- Cross-platform parity: web (`useVoiceCall.ts`) and Kotlin Android app both work via the same LiveKit room contract — no per-platform branching

## Non-goals

- Speculative LLM start on interim transcripts (fragile, thrashes Brain)
- Opener / instant-ack audio files (gimmicky for English personal-assistant use)
- Multi-language detection mid-call (language fixed per session)
- Recording, voice authentication, audio analytics
- Voice-side fallback STT/TTS providers (single-vendor: Sarvam)

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| STT | Sarvam streaming (interim + final) | Already coded, key in `.env`, multilingual |
| TTS | Sarvam `bulbul:v3` (new plugin) | Single-vendor consolidation with STT |
| Turn detection | LiveKit `turn-detector` EOU transformer + Silero VAD two-stage | Semantic turn detection prevents mid-thought cutoffs |
| Barge-in | Hard cancel with 500 ms duration gate | Filters coughs/acks without intent-classifier complexity |
| Latency target | <1.5 s median, <2.5 s p95 | Standard streaming setup hits this without speculative LLM |
| Architecture | Hybrid — patch `voice_manager.py`, extract three new modules | Right balance: isolate the broken parts, keep the working LiveKit boilerplate |

## Architecture

```
[mic frames] ── LiveKit room
      │
      ▼
  Silero VAD ─── speech_start ────────────────────────┐
      │         │                                      │
      │         └──> BargeInController                 │
      │                  │ (if TTS active + ≥500ms)    │
      │                  └──> session.interrupt()      │
      ▼                                                ▼
  speech_end ──> SarvamSTT (streaming, interim+final) ─┘
                       │
                       │ final transcript
                       ▼
              EOU Transformer ── "complete?" ── no ──> keep listening
                       │ yes
                       ▼
                  Brain.handle()
                       │
                       │ (chunks → hub queue, async)
                       ▼
              SentencePump
                  ├─ buffer chunks
                  ├─ split on .?! (hard) | , @120ch (soft)
                  └─ emit each sentence ──> SarvamTTS.synthesize()
                                                    │
                                                    │ stream PCM frames
                                                    ▼
                                             LiveKit room ──> [client speaker]
```

### Latency budget

| Stage | Target |
|---|---|
| VAD silence detect | ~200 ms |
| STT final after end-of-speech | ~250 ms |
| EOU check | ~50 ms |
| Brain first-chunk | ~400-600 ms |
| Sentence buffer + TTS first-byte | ~300 ms |
| LiveKit playout | ~100 ms |
| **Median total** | **~1.3 s** |

Headroom keeps p95 ≤ 2.5 s.

## Components

### New modules

#### `neurocomputer/core/voice/sarvam_tts.py` (~150 lines)

- Class `SarvamTTS(livekit.agents.tts.TTS)` — implements LiveKit's TTS plugin interface
- Wraps Sarvam `bulbul:v3` HTTP+streaming endpoint
- Method `synthesize(text) -> AsyncIterator[AudioFrame]` — yields PCM frames as Sarvam streams them
- Config (env vars): `SARVAM_VOICE_ID` (default `meera`), `SARVAM_TTS_LANGUAGE` (default `en-IN`), sample rate fixed at 24000
- Auth: `SARVAM_API_KEY` from env (already present)
- Used by: `voice_manager.py`

#### `neurocomputer/core/voice/sentence_pump.py` (~200 lines)

- Class `SentencePump(llm.LLM)` — replaces `InfinityBrainLLM` + `InfinityBrainStream`
- Subscribes to Brain hub queue, buffers char-by-char until sentence boundary
- Boundary rules (checked in this priority order, first match wins):
  1. **Hard split** on regex `[.!?।]\s` (period/exclaim/question/devanagari danda + whitespace) — anywhere in buffer
  2. **Soft split** on regex `[,;:]\s` only when `len(buf) >= 120`
  3. **Force flush** at last whitespace when `len(buf) >= 240` (paranoia bound for unpunctuated chunks)
  4. **Final flush** of remainder on `task.done`
- Trailing whitespace requirement on hard-end avoids splitting decimals (`3.14`) and abbreviations (`Mr.`)
- Emits each sentence as a `ChatChunk` to LiveKit's TTS pipeline → fires Sarvam synthesis immediately
- 15s watchdog on `hub_queue.get()`; on timeout emits apology sentence and ends turn
- Ignores all event types except `assistant` (silently drops `node.start`, `node.done`, tool-call events)

#### `neurocomputer/core/voice/barge_in.py` (~80 lines)

State machine:

```
IDLE ── user_started_speaking ──> ARMED (start 500ms timer)
ARMED ── user_stopped_speaking ─> IDLE   (no cancel — was cough/ack)
ARMED ── timer expires ─────────> CANCELLING
CANCELLING:
  if agent currently producing speech (check via session state — exact attr resolved at impl time):
    session.interrupt()       # clears TTS queue, cancels Sarvam stream
    log "barge-in fired"
  state ── user_stopped_speaking ──> IDLE
```

- Listens to `AgentSession` `user_started_speaking` / `user_stopped_speaking` events
- Timer cancelled on session close
- Built-in `AgentSession.allow_interruptions` set to `False` so this controller is the sole barge-in path

### Patches to existing files

#### `neurocomputer/core/voice_manager.py`

- Swap `openai.STT(model="whisper-1")` → `SarvamSTT(streaming=True, interim_results=True)`
- Swap `openai.TTS(...)` → `SarvamTTS(...)`
- Add `livekit.plugins.turn_detector.EOUModel(unlikely_threshold=0.15)` to `AgentSession(turn_detection=...)`
- Replace `InfinityBrainLLM` instance with `SentencePump`
- Mount `BargeInController` after `AgentSession` start, wire to its events
- Tighten Silero VAD: `min_silence_duration_ms=200` (was 300)
- Set `allow_interruptions=False` on `AgentSession`
- Delete: `InfinityBrainLLM`, `InfinityBrainStream`, `_run` method (~180 lines removed)

#### `pyproject.toml` / requirements

- Add `livekit-plugins-turn-detector`
- Keep `livekit-plugins-silero`
- Verify `livekit-plugins-openai` still needed elsewhere; remove imports from `voice_manager.py` regardless

### Files unchanged

- `useVoiceCall.ts`, `services/livekit.ts`, Kotlin LiveKit client — same room contract
- `server.py:/voice/token` endpoint
- `brain.py` — already publishes chunks correctly
- `sarvam_stt.py` — already streaming, just becomes wired

### Files deleted / cleaned

- OpenAI STT/TTS imports + instances in `voice_manager.py`
- `faster_whisper_stt.py` — verify unused, then delete

## Turn detection details

**Stage 1 (Silero VAD, retuned):** `min_silence_duration_ms=200`, `min_speech_duration_ms=50`, `activation_threshold=0.25`. Fires `user_started_speaking` / `user_stopped_speaking`.

**Stage 2 (EOU transformer):** `livekit/turn-detector-multilingual` model (~50 MB, downloads on first use, cached). Fires only on `user_stopped_speaking` with latest STT final transcript available.

Threshold behavior:
- `prob ≥ 0.5` → fire LLM turn immediately
- `0.15 ≤ prob < 0.5` → wait 500 ms more for continued speech
- `prob < 0.15` → wait 1500 ms (very likely incomplete)

Net effect: "call mom… and dad" no longer cuts after "call mom" because EOU sees incomplete intent. "what time is it" fires immediately.

## Error handling

| Failure | Behavior |
|---|---|
| Sarvam STT 5xx | `AgentSession` error event → log + Sarvam-TTS error message → end turn cleanly. No fallback STT. |
| Sarvam TTS 5xx (per sentence) | Catch in plugin → log → yield silence frame → continue. 3 consecutive failures → end turn silently. |
| Brain stalls >15s | `SentencePump` watchdog → apology sentence → break loop. |
| EOU model fails to load | Log warning at startup → fall back to VAD-only turn detection. Voice still works. |
| Sarvam STT segment cap (~60 s) | Final transcript fires automatically; long monologues handled by Sarvam. |
| Two voice calls per user (web + mobile) | Verify `voice_manager.start_call()` issues unique room per call. Fix if collision. |
| LiveKit reconnect mid-turn | LiveKit auto-reconnect; in-flight TTS truncates cleanly if Sarvam stream broken. |
| Resource cleanup | `BargeInController` timer cancelled on session close. Sarvam HTTP pool `aclose()` on session end. EOU model singleton across sessions. |

## Telemetry

Single-user assistant → structured logs only. Per-turn fields:
- `vad_to_stt_final_ms`
- `stt_final_to_eou_ms`
- `eou_to_brain_first_chunk_ms`
- `brain_first_chunk_to_first_tts_byte_ms`
- `total_speech_end_to_first_audio_ms`  (headline)
- `barge_in_fired` (bool)

No dashboards, no Prometheus — grep logs when investigating.

## Testing

### Unit (real, fast, mocked externals)

- **`test_sentence_pump.py`** — synthetic chunk streams, assert sentence boundaries
  - Hard-end split, soft-end at 120 ch, force-flush at 240 ch
  - Decimals not split (`3.14`)
  - Abbreviations (`Mr. Smith`)
  - Devanagari danda (`।`)
  - Brain hub mocked with `asyncio.Queue`
- **`test_barge_in.py`** — feed VAD events, assert state machine
  - Cough <500 ms (no cancel)
  - Real interrupt ≥500 ms (cancel)
  - TTS not active (no-op)
  - Rapid stop-start sequence
  - LiveKit `AgentSession.interrupt()` recorded as call

### Integration (gated by `RUN_LIVE_TESTS=1`)

- **`test_sarvam_tts_live.py`** — hits real Sarvam, asserts non-empty PCM with valid sample rate
- **`test_sarvam_stt_live.py`** — verify exists or stub

### Manual smoke

- Web: open call from browser. Validate
  - First audio < 1.5 s after speech end
  - Barge-in cancels mid-sentence (>500 ms speech)
  - "call mom and dad" doesn't split into two turns
  - Cough mid-response doesn't cancel
- Mobile: same checks on Kotlin app
- Latency log greps: `total_speech_end_to_first_audio_ms` p95 ≤ 2500

### Out of test scope

EOU model accuracy (not our model), LiveKit internals, Brain DAG (existing tests cover).

## Rollout

Single-user assistant → no canary, no flag, no dual-write.

1. New modules land first (sarvam_tts, sentence_pump, barge_in) with unit tests — no behavior change.
2. `voice_manager.py` patch flips wiring atomically — old code paths deleted in same commit.
3. First post-deploy call: run manual smoke checklist.
4. If broken: `git revert`. Voice falls back to old slow path. Text chat unaffected.

## Acceptance gate

- Median speech-end-to-first-audio < 1.5 s
- p95 < 2.5 s
- Validated across ~20 manual turns post-deploy via headline metric in logs
- If miss: identify exceeded stage from per-stage timing → tune

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sarvam TTS plugin bug, garbled audio | Med | Unit-test PCM frame format; smoke-test before merge |
| EOU model adds >100 ms latency | Low | Plugin runs CPU-async; if hot, lower threshold to favor fire-fast |
| Brain emits per-token chunks → flood of tiny TTS calls | Low | `SOFT_MIN_CHARS=120` already handles; verify in smoke |
| 500 ms barge-in gate feels laggy | Med | Tunable constant; can drop to 300 ms post-deploy |
| `voice_manager.py` patches conflict with active sessions during deploy | Low | Restart agent worker; no in-flight calls expected |
