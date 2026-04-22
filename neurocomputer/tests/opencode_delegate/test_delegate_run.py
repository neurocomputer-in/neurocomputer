"""Integration tests for the full opencode_delegate.run() entry point."""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, "/home/ubuntu/neurocomputer-dev")

from tests.opencode_delegate.stub_opencode import StubOpenCode


def _setup_stub_env(stub: StubOpenCode) -> str:
    """Point the delegate at the stub, and use an isolated session-map file."""
    os.environ["OPENCODE_SERVER_URL"] = stub.url
    tmpdir = tempfile.mkdtemp(prefix="oc_deleg_")
    os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "conversations"), exist_ok=True)
    os.chdir(tmpdir)
    return tmpdir


def _clear_delegate_modules() -> None:
    """Force a fresh import of the delegate so module-level state (cwd-
    dependent paths, the singleton SSEConsumer) is reset per test."""
    for m in list(sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            sys.modules.pop(m, None)


async def _drain_stream(collected: list, chunk: str) -> None:
    collected.append(chunk)


def _stream_cb_for(collected: list):
    """Return an async stream_callback that appends to the given list."""
    async def cb(chunk: str) -> None:
        collected.append(chunk)
    return cb


async def test_happy_path_single_turn_streams_and_returns_text():
    """One user turn: stub emits busy → delta 'hi' → delta ' there' → assistant
    completion with finish=stop. Delegate must return 'hi there' and stream
    each delta via stream_callback in order."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        collected: list[str] = []
        state = {"__stream_cb": _stream_cb_for(collected),
                 "__cid": "cid-happy", "__pub": None}

        delegate_task = asyncio.create_task(delegate.run(state, task="hi"))

        # Wait for the delegate's POST.
        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if user_posts:
                break
            await asyncio.sleep(0.02)
        assert user_posts, "delegate never POSTed"
        posted = user_posts[-1]
        sid = posted["sid"]
        user_msg_id = posted["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": user_msg_id,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_asst_1",
                            "partID": "prt_1", "field": "text", "delta": "hi"}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_asst_1",
                            "partID": "prt_1", "field": "text", "delta": " there"}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": user_msg_id,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 1, "completed": 2}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        # Trigger flush via side-channel POST.
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig_happy", "parts": []})

        result = await asyncio.wait_for(delegate_task, timeout=10)
        assert result["status"] == "success", result
        assert result["response"] == "hi there", f"response={result['response']!r}"
        assert "".join(collected) == "hi there", f"streamed={collected!r}"
        print("✅ happy-path single turn")
    finally:
        # Stop the delegate's background SSE consumer before stub shuts down.
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
        except Exception:
            pass
        await stub.stop()


async def test_two_rapid_turns_on_same_conversation_both_get_replies():
    """Concurrency regression: two run() calls on the same cid launched
    back-to-back must both produce replies, in order."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        collected1: list[str] = []
        collected2: list[str] = []
        state1 = {"__stream_cb": _stream_cb_for(collected1),
                  "__cid": "cid-rapid", "__pub": None}
        state2 = {"__stream_cb": _stream_cb_for(collected2),
                  "__cid": "cid-rapid", "__pub": None}

        task1 = asyncio.create_task(delegate.run(state1, task="first"))
        task2 = asyncio.create_task(delegate.run(state2, task="second"))

        async def servicer():
            seen = 0
            while seen < 2:
                user_posts = [p for p in stub.post_log
                              if p["body"].get("messageID", "").startswith("msg_")]
                while len(user_posts) <= seen:
                    await asyncio.sleep(0.02)
                    user_posts = [p for p in stub.post_log
                                  if p["body"].get("messageID", "").startswith("msg_")]
                posted = user_posts[seen]
                sid = posted["sid"]
                umid = posted["body"]["messageID"]
                aid = f"msg_asst_{seen+1}"
                stub.script_turn(sid, [
                    {"type": "session.status",
                     "properties": {"sessionID": sid, "status": {"type": "busy"}}},
                    {"type": "message.updated",
                     "properties": {"sessionID": sid,
                                    "info": {"id": aid, "parentID": umid,
                                             "role": "assistant",
                                             "time": {"created": 1}}}},
                    {"type": "message.part.delta",
                     "properties": {"sessionID": sid, "messageID": aid,
                                    "partID": f"prt_{seen+1}", "field": "text",
                                    "delta": f"reply{seen+1}"}},
                    {"type": "message.updated",
                     "properties": {"sessionID": sid,
                                    "info": {"id": aid, "parentID": umid,
                                             "role": "assistant", "finish": "stop",
                                             "time": {"created": 1, "completed": 2}}}},
                    {"type": "session.status",
                     "properties": {"sessionID": sid, "status": {"type": "idle"}}},
                ])
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    await s.post(f"{stub.url}/session/{sid}/message",
                                 json={"messageID": f"trig_{seen}", "parts": []})
                seen += 1

        servicer_task = asyncio.create_task(servicer())

        r1 = await asyncio.wait_for(task1, timeout=10)
        r2 = await asyncio.wait_for(task2, timeout=10)
        await servicer_task

        assert r1["status"] == "success" and r1["response"] == "reply1", r1
        assert r2["status"] == "success" and r2["response"] == "reply2", r2
        assert "".join(collected1) == "reply1"
        assert "".join(collected2) == "reply2"
        print("✅ two rapid turns both get replies")
    finally:
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
        except Exception:
            pass
        await stub.stop()


async def test_multi_step_tool_call_turn_returns_final_text_only_after_stop():
    """Turn has two assistant messages under same parentID: first has
    finish='tool-calls' (intermediate — must NOT terminate), second has
    finish='stop' (terminal). Tool events must be forwarded via pub."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        tool_events: list[dict] = []
        step_events: list[dict] = []

        async def pub(topic: str, payload: dict) -> None:
            if topic == "opencode.tool":
                tool_events.append(payload)
            elif topic == "opencode.step":
                step_events.append(payload)

        collected: list[str] = []
        state = {"__stream_cb": _stream_cb_for(collected),
                 "__cid": "cid-tools", "__pub": pub}

        task = asyncio.create_task(delegate.run(state, task="do a tool thing"))

        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if user_posts:
                break
            await asyncio.sleep(0.02)
        assert user_posts
        sid = user_posts[-1]["sid"]
        umid = user_posts[-1]["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_step1", "messageID": "msg_asst_1",
                                     "type": "step-start"}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_tool1", "messageID": "msg_asst_1",
                                     "type": "tool", "tool": "read",
                                     "callID": "call_1",
                                     "state": {"status": "completed",
                                               "input": {"filePath": "/x"},
                                               "output": "file contents",
                                               "title": "Read /x"}}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_stepf1", "messageID": "msg_asst_1",
                                     "type": "step-finish",
                                     "reason": "tool-calls",
                                     "tokens": {"input": 10, "output": 2}}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": umid,
                                     "role": "assistant", "finish": "tool-calls",
                                     "time": {"created": 1, "completed": 2}}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_2", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 3}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_asst_2",
                            "partID": "prt_text", "field": "text",
                            "delta": "done!"}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_2", "parentID": umid,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 3, "completed": 4}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})

        result = await asyncio.wait_for(task, timeout=10)
        assert result["status"] == "success", result
        assert result["response"] == "done!", f"got {result['response']!r}"
        assert any(e["tool"] == "read" for e in tool_events), tool_events
        assert any(e["type"] == "step-finish" for e in step_events), step_events
        print("✅ multi-step tool-call turn")
    finally:
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
        except Exception:
            pass
        await stub.stop()


async def test_model_error_surfaces_as_error_reply_not_timeout():
    """If opencode emits message.updated with info.error, the delegate
    returns status=error with the error message — no 300s timeout."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        state = {"__stream_cb": _stream_cb_for([]),
                 "__cid": "cid-err", "__pub": None}
        task = asyncio.create_task(delegate.run(state, task="x"))

        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if user_posts:
                break
            await asyncio.sleep(0.02)
        sid = user_posts[-1]["sid"]
        umid = user_posts[-1]["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a", "parentID": umid,
                                     "role": "assistant",
                                     "error": {"name": "ProviderAuthError",
                                               "data": {"message": "model not found",
                                                        "providerID": "ollama"}},
                                     "time": {"created": 1}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})

        result = await asyncio.wait_for(task, timeout=10)
        assert result["status"] == "error"
        assert "model not found" in result["response"], result
        print("✅ model error surfaces in reply")
    finally:
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
        except Exception:
            pass
        await stub.stop()


async def test_second_turn_waits_for_idle_before_posting():
    """If bus.status=='busy' at run() entry, the POST does NOT fire until
    bus.idle_ev is set by an 'idle' session.status event."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        state1 = {"__stream_cb": _stream_cb_for([]), "__cid": "cid-gate", "__pub": None}
        state2 = {"__stream_cb": _stream_cb_for([]), "__cid": "cid-gate", "__pub": None}

        t1 = asyncio.create_task(delegate.run(state1, task="t1"))
        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if user_posts:
                break
            await asyncio.sleep(0.02)
        sid = user_posts[-1]["sid"]
        umid1 = user_posts[-1]["body"]["messageID"]

        # Session goes busy + one assistant message created (no finish yet).
        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a1", "parentID": umid1,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig1", "parts": []})

        # Launch turn 2 — must block on bus.lock (held by t1).
        t2 = asyncio.create_task(delegate.run(state2, task="t2"))
        await asyncio.sleep(0.5)
        user_posts_now = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
        assert len(user_posts_now) == 1, \
            f"turn 2 POSTed while session was busy: {user_posts_now}"

        # Finish turn 1.
        stub.script_turn(sid, [
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a1", "parentID": umid1,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 1, "completed": 2}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig_f1", "parts": []})

        r1 = await asyncio.wait_for(t1, timeout=10)
        assert r1["status"] == "success"

        # Turn 2 should now POST. Fresh-session-per-turn means turn 2's POST
        # lands on a different opencode sid; look up the newest user POST
        # and script events for THAT sid.
        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if len(user_posts) >= 2:
                break
            await asyncio.sleep(0.02)
        sid2 = user_posts[-1]["sid"]
        umid2 = user_posts[-1]["body"]["messageID"]
        stub.script_turn(sid2, [
            {"type": "session.status",
             "properties": {"sessionID": sid2, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid2,
                            "info": {"id": "msg_a2", "parentID": umid2,
                                     "role": "assistant",
                                     "time": {"created": 3}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid2, "messageID": "msg_a2",
                            "partID": "p", "field": "text", "delta": "ok"}},
            {"type": "message.updated",
             "properties": {"sessionID": sid2,
                            "info": {"id": "msg_a2", "parentID": umid2,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 3, "completed": 4}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid2, "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid2}/message",
                         json={"messageID": "trig_f2", "parts": []})
        r2 = await asyncio.wait_for(t2, timeout=10)
        assert r2["status"] == "success" and r2["response"] == "ok", r2
        print("✅ cid lock delays second turn's POST")
    finally:
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
        except Exception:
            pass
        await stub.stop()


async def test_reconnect_mid_turn_times_out_cleanly_with_partial_text():
    """If SSE drops mid-turn and nothing more arrives, the delegate times
    out cleanly within _TURN_TIMEOUT with an error reply carrying any
    partial text accumulated before the drop."""
    _clear_delegate_modules()
    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate
        delegate._TURN_TIMEOUT = 1.5  # shorten for the test

        collected: list[str] = []
        state = {"__stream_cb": _stream_cb_for(collected),
                 "__cid": "cid-drop", "__pub": None}

        task = asyncio.create_task(delegate.run(state, task="x"))

        for _ in range(100):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if user_posts:
                break
            await asyncio.sleep(0.02)
        sid = user_posts[-1]["sid"]
        umid = user_posts[-1]["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_a",
                            "partID": "p", "field": "text", "delta": "partial"}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})
        await asyncio.sleep(0.2)
        await stub.stop()

        result = await asyncio.wait_for(task, timeout=5)
        assert result["status"] == "error"
        assert "timed out" in result["response"].lower(), result
        assert "partial" in "".join(collected), \
            f"partial text lost: {collected!r}"
        print("✅ mid-turn SSE drop → clean timeout with partial text")
    finally:
        try:
            from neuros.opencode_delegate import code as delegate
            if getattr(delegate, "_consumer", None) is not None:
                await delegate._consumer.stop()
                delegate._consumer = None
            delegate._TURN_TIMEOUT = 300.0
        except Exception:
            pass
        try:
            await stub.stop()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(test_happy_path_single_turn_streams_and_returns_text())
    asyncio.run(test_two_rapid_turns_on_same_conversation_both_get_replies())
    asyncio.run(test_multi_step_tool_call_turn_returns_final_text_only_after_stop())
    asyncio.run(test_model_error_surfaces_as_error_reply_not_timeout())
    asyncio.run(test_second_turn_waits_for_idle_before_posting())
    asyncio.run(test_reconnect_mid_turn_times_out_cleanly_with_partial_text())
    print("\n=== delegate run() tests (6/6) passed ===")
