#!/usr/bin/env python3
"""
automated_test_client.py – head-less test driver for Neo

Usage
-----
# run an interactive session (unchanged)
python automated_test_client.py

# run a scripted test
python automated_test_client.py --scenario tests/hello_world.json
"""
import asyncio, json, uuid, argparse, signal, sys, os, requests, websockets
from typing import Dict, Any, List
from dataclasses import dataclass
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# 1.  tiny shim: pull most of the old code in unchanged
# ---------------------------------------------------------------------------
from cli_client import NeoClient, Config        # your original file

# ---------------------------------------------------------------------------
# 2.  Automated runner
# ---------------------------------------------------------------------------
class ScenarioRunner(NeoClient):
    def __init__(self, config: Config, steps: List[Dict[str, str]]):
        super().__init__(config)
        self.steps         = steps
        self.current_index = 0
        self.step_release  = asyncio.Event()
        self.waiting_for_reply = False           # ← new

    # ---------- tiny hook -----------------------------------------
    def _display_message(self, sender: str, text: str, message_type: str = "content"):
        super()._display_message(sender, text, message_type)
        # when node n0 completes, parent prints "✓ Node n0   (neuro: …)"
        if sender == "system" and text.startswith("✓ Node n0"):
            self.step_release.set()
            self.waiting_for_reply = False

        # fast-path turns (no DAG) arrive as a single assistant message
        if sender == "assistant" and self.waiting_for_reply:
            self.step_release.set()
            self.waiting_for_reply = False
    # --------------------------------------------------------------

    async def _drive_script(self):
        while self.current_index < len(self.steps):
            text = self.steps[self.current_index]["text"]
            self._display_message("user", text)          # echo to console
            if not await self._send_message(text):
                console.print("[red]❌ failed to send, aborting")
                return
            self.waiting_for_reply = True                # expect a reply
            await self.step_release.wait()               # wait for DAG *or* direct reply
            self.step_release.clear()
            self.current_index += 1
        await asyncio.sleep(1)                           # flush tail output
        self.exit_flag.set()

    async def start(self):
        if not await self._connect_websocket():
            console.print("[red]Server offline?")
            return
        handler = asyncio.create_task(self._handle_websocket_messages())  # ← parent's original
        driver  = asyncio.create_task(self._drive_script())
        await asyncio.wait([handler, driver], return_when=asyncio.FIRST_COMPLETED)
        handler.cancel(); driver.cancel()
        try: await self.ws.close()
        except: pass

# ---------------------------------------------------------------------------
# 3.  command-line glue
# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Infinity automated test-runner (requires a JSON scenario)"
    )
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=7000)
    p.add_argument("--cid",  default="")
    p.add_argument("--dev",  action="store_true")
    p.add_argument("--debug",action="store_true")
    p.add_argument("--no-dag",action="store_true")

    # make the scenario a *positional* argument → mandatory
    p.add_argument("scenario", help="Path to JSON file with scripted user lines")

    return p.parse_args()

async def main():
    args = parse_args()
    cfg  = Config(
        host=args.host, port=args.port, cid=args.cid,
        dev_mode=args.dev, debug=args.debug, show_dag=not args.no_dag
    )

    # scenario is now a positional argument, so it's always present
    with open(args.scenario, encoding="utf-8") as f:
        steps = json.load(f)                   # list[dict]; at minimum {"text": "..."}
    await ScenarioRunner(cfg, steps).start()

if __name__ == "__main__":
    asyncio.run(main())
