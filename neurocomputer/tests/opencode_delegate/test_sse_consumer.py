"""Unit tests for SSEConsumer envelope parsing, routing, and reconnect."""
import asyncio
import sys

sys.path.insert(0, "/home/ubuntu/neurocomputer-dev")

from neuros.opencode_delegate.sse_consumer import SSEConsumer
from tests.opencode_delegate.stub_opencode import StubOpenCode


async def test_parses_v146_envelope_and_routes_to_session_bus():
    """Events arrive as {directory, project, payload: {type, properties}}.
    The consumer must extract payload.{type,properties} and route by
    properties.sessionID into the right SessionBus.queue."""
    stub = StubOpenCode()
    await stub.start()
    consumer = None
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus_a = consumer.bus_for("ses_A")

        # Give the consumer time to open the SSE connection.
        await asyncio.sleep(0.2)

        # Script a delta, then trigger flush via POST.
        stub.script_turn("ses_A", [
            {"type": "message.part.delta",
             "properties": {"sessionID": "ses_A", "messageID": "msg_1",
                            "partID": "prt_1", "field": "text", "delta": "hello"}}
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_A/message",
                         json={"messageID": "msg_u1", "parts": []})

        evt = await asyncio.wait_for(bus_a.queue.get(), timeout=2.0)
        assert evt["type"] == "message.part.delta", f"got type={evt['type']!r}"
        assert evt["properties"]["delta"] == "hello"
        assert evt["properties"]["sessionID"] == "ses_A"
        print("✅ envelope parsed & routed")
    finally:
        if consumer:
            await consumer.stop()
        await stub.stop()


async def test_events_are_filtered_by_sessionID():
    """An event for ses_A must only appear in bus_for('ses_A'), not in bus_for('ses_B')."""
    stub = StubOpenCode()
    await stub.start()
    consumer = None
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus_a = consumer.bus_for("ses_A")
        bus_b = consumer.bus_for("ses_B")
        await asyncio.sleep(0.2)

        stub.script_turn("ses_A", [
            {"type": "message.part.delta",
             "properties": {"sessionID": "ses_A", "field": "text", "delta": "A"}}
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_A/message",
                         json={"messageID": "m", "parts": []})

        evt = await asyncio.wait_for(bus_a.queue.get(), timeout=2.0)
        assert evt["properties"]["delta"] == "A"
        assert bus_b.queue.empty(), "bus_B leaked an event from ses_A"
        print("✅ session filtering correct")
    finally:
        if consumer:
            await consumer.stop()
        await stub.stop()


async def test_session_status_tracks_busy_and_idle():
    """session.status events flip bus.status and bus.idle_ev accordingly."""
    stub = StubOpenCode()
    await stub.start()
    consumer = None
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus = consumer.bus_for("ses_S")
        await asyncio.sleep(0.2)

        stub.script_turn("ses_S", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_S", "status": {"type": "busy"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_S/message",
                         json={"messageID": "m", "parts": []})

        for _ in range(20):
            if bus.status == "busy":
                break
            await asyncio.sleep(0.05)
        assert bus.status == "busy", f"expected busy, got {bus.status}"
        assert not bus.idle_ev.is_set(), "idle_ev must be clear when busy"

        stub.script_turn("ses_S", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_S", "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_S/message",
                         json={"messageID": "m2", "parts": []})

        await asyncio.wait_for(bus.idle_ev.wait(), timeout=2.0)
        assert bus.status == "idle"
        print("✅ session.status tracking correct")
    finally:
        if consumer:
            await consumer.stop()
        await stub.stop()


async def test_reconnects_after_sse_drop_and_marks_status_unknown():
    """If the SSE connection fails, the consumer reconnects, and any known
    bus statuses are reset to 'unknown' so the next turn re-gates."""
    stub = StubOpenCode()
    await stub.start()
    consumer = None
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus = consumer.bus_for("ses_R")
        await asyncio.sleep(0.2)

        # Put the bus into idle state first.
        stub.script_turn("ses_R", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_R", "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_R/message",
                         json={"messageID": "m", "parts": []})
        await asyncio.wait_for(bus.idle_ev.wait(), timeout=2.0)
        assert bus.status == "idle"

        # Stop the stub → current SSE stream dies → consumer hits except
        # branch → marks all buses 'unknown' and waits for reconnect.
        await stub.stop()

        for _ in range(60):
            if bus.status == "unknown":
                break
            await asyncio.sleep(0.1)
        assert bus.status == "unknown", f"expected unknown after drop, got {bus.status}"
        assert not bus.idle_ev.is_set()
        print("✅ reconnect resets bus status to unknown")
    finally:
        if consumer:
            await consumer.stop()
        try:
            await stub.stop()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(test_parses_v146_envelope_and_routes_to_session_bus())
    asyncio.run(test_events_are_filtered_by_sessionID())
    asyncio.run(test_session_status_tracks_busy_and_idle())
    asyncio.run(test_reconnects_after_sse_drop_and_marks_status_unknown())
    print("\n=== SSE consumer tests (4/4) passed ===")
