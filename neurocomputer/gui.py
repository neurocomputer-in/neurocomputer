#!/usr/bin/env python3
"""
GUI Automator CLI — run GUI automation neuros from the command line.

Usage:
  gui screenshot [--region X Y W H]
  gui read       [--question "What is on screen?"]
  gui find       "Submit button"
  gui click      "Submit button"
  gui click      --xy 400 300
  gui type       "Hello world" [--target "Search box"]
  gui record     my_workflow
  gui replay     my_workflow
"""

import asyncio
import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def cmd_screenshot(args):
    from core.gui_automator.screen_capture import capture_full, capture_region
    import time

    if args.region:
        img = capture_region(*args.region)
    else:
        img = capture_full()

    os.makedirs("gui_screenshots", exist_ok=True)
    path = f"gui_screenshots/capture_{int(time.time())}.png"
    img.save(path)
    print(f"✅ Screenshot saved: {path}")
    print(f"   Size: {img.width}x{img.height}")

async def cmd_read(args):
    from core.gui_automator.screen_capture import capture_full
    from core.gui_automator.vision_engine import QwenVLEngine, OCREngine

    img = capture_full()

    print("🔍 Running OCR...")
    ocr = OCREngine()
    text = ocr.extract_text(img)

    print("🧠 Running Qwen-VL...")
    vlm = QwenVLEngine()
    prompt = args.question or "Describe the current screen and its main interactive elements."
    description = await vlm.describe_screen(img, prompt=prompt)

    print(f"\n{'='*60}")
    print("VLM Description:")
    print(f"{'='*60}")
    print(description)
    print(f"\n{'='*60}")
    print("OCR Text:")
    print(f"{'='*60}")
    print(text.strip()[:500])

async def cmd_find(args):
    from core.gui_automator.screen_capture import capture_full
    from core.gui_automator.element_detector import ElementDetector
    from core.gui_automator.vision_engine import QwenVLEngine

    img = capture_full()
    vlm = QwenVLEngine()
    detector = ElementDetector(vlm_engine=vlm)

    print(f"🔍 Searching for: '{args.description}'...")
    result = await detector.find_element(img, args.description, force_method=args.method)

    if result:
        print(f"✅ Found! x={result['x']}, y={result['y']}, w={result['w']}, h={result['h']}")
        print(f"   Method: {result['method']}  Confidence: {result['confidence']}")
    else:
        print("❌ Element not found.")

async def cmd_click(args):
    from core.gui_automator.action_executor import ActionExecutor

    executor = ActionExecutor()

    if args.xy:
        x, y = args.xy
        await executor.click(x, y)
        print(f"✅ Clicked at ({x}, {y})")
    elif args.description:
        from core.gui_automator.screen_capture import capture_full
        from core.gui_automator.element_detector import ElementDetector
        from core.gui_automator.vision_engine import QwenVLEngine

        img = capture_full()
        vlm = QwenVLEngine()
        detector = ElementDetector(vlm_engine=vlm)

        print(f"🔍 Finding '{args.description}'...")
        result = await detector.find_element(img, args.description)
        if result:
            x = result["x"] + result["w"] // 2
            y = result["y"] + result["h"] // 2
            await executor.click(x, y)
            print(f"✅ Clicked '{args.description}' at ({x}, {y})")
        else:
            print("❌ Element not found.")
    else:
        print("❌ Provide --xy X Y or a description.")

async def cmd_type(args):
    from core.gui_automator.action_executor import ActionExecutor

    executor = ActionExecutor()

    if args.target:
        from core.gui_automator.screen_capture import capture_full
        from core.gui_automator.element_detector import ElementDetector
        from core.gui_automator.vision_engine import QwenVLEngine

        img = capture_full()
        vlm = QwenVLEngine()
        detector = ElementDetector(vlm_engine=vlm)

        result = await detector.find_element(img, args.target)
        if result:
            x = result["x"] + result["w"] // 2
            y = result["y"] + result["h"] // 2
            await executor.click(x, y)
        else:
            print(f"❌ Target '{args.target}' not found.")
            return

    await executor.type_text(args.text)
    print(f"✅ Typed: '{args.text}'")

async def cmd_record(args):
    from core.gui_automator.workflow_recorder import WorkflowRecorder

    recorder = WorkflowRecorder()
    recorder.start_recording(args.name)
    print(f"🎥 Recording started: '{args.name}'")
    print("   (Recording is passive — actions are logged when invoked via other commands)")
    # In a real interactive mode you'd hook into input events here

async def cmd_replay(args):
    from core.gui_automator.workflow_recorder import WorkflowRecorder
    from core.gui_automator.action_executor import ActionExecutor
    from core.gui_automator.element_detector import ElementDetector
    from core.gui_automator.vision_engine import QwenVLEngine
    from core.gui_automator.screen_capture import capture_full

    filepath = os.path.join("workflows", f"{args.name}.json")
    if not os.path.exists(filepath):
        print(f"❌ Workflow '{args.name}' not found at {filepath}")
        return

    with open(filepath) as f:
        workflow = json.load(f)

    executor = ActionExecutor()
    vlm = QwenVLEngine()
    detector = ElementDetector(vlm_engine=vlm)

    print(f"🔄 Replaying workflow: '{args.name}' ({len(workflow['steps'])} steps)")
    for i, step in enumerate(workflow["steps"], 1):
        action = step.get("action")
        target = step.get("target", "")
        print(f"  Step {i}: {action} → {target}")

        if action == "click":
            coords = step.get("coords")
            if target:
                img = capture_full()
                result = await detector.find_element(img, target)
                if result:
                    x = result["x"] + result["w"] // 2
                    y = result["y"] + result["h"] // 2
                    await executor.click(x, y)
                elif coords:
                    await executor.click(coords[0], coords[1])
                else:
                    print(f"    ❌ Could not find '{target}'")
            elif coords:
                await executor.click(coords[0], coords[1])

        elif action == "type":
            text = step.get("text", "")
            await executor.type_text(text)

    print(f"✅ Replay complete!")

async def cmd_automate(args):
    """Run the autonomous GUI agent with a natural language task."""
    # Import and run the gui_automate neuro directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("gui_automate",
        os.path.join(os.path.dirname(__file__), "neuros/gui_automate/code.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    state = {}
    result = await mod.run(state, task=args.task, max_steps=args.max_steps)
    
    print(f"\n{'='*60}")
    print(f"Result: {result['result']}")
    print(f"Steps taken: {len(result.get('steps_taken', []))}")
    for step in result.get("steps_taken", []):
        print(f"  Step {step['step']}: {step['action']}")


def main():
    parser = argparse.ArgumentParser(
        prog="gui",
        description="GUI Task Automator — automate desktop actions via VLM, OCR, and template matching",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # screenshot
    p = sub.add_parser("screenshot", aliases=["ss"], help="Take a screenshot")
    p.add_argument("--region", type=int, nargs=4, metavar=("X", "Y", "W", "H"), help="Crop region")

    # read
    p = sub.add_parser("read", help="Read/describe the screen via VLM + OCR")
    p.add_argument("--question", "-q", type=str, help="Ask a specific question about the screen")

    # find
    p = sub.add_parser("find", help="Find a UI element by description")
    p.add_argument("description", type=str, help="Element description")
    p.add_argument("--method", type=str, choices=["vlm", "ocr", "pattern"], help="Force detection method")

    # click
    p = sub.add_parser("click", help="Click an element by description or coordinates")
    p.add_argument("description", type=str, nargs="?", help="Element description")
    p.add_argument("--xy", type=int, nargs=2, metavar=("X", "Y"), help="Click at exact coordinates")

    # type
    p = sub.add_parser("type", help="Type text (optionally into a target element)")
    p.add_argument("text", type=str, help="Text to type")
    p.add_argument("--target", "-t", type=str, help="Element to click before typing")

    # record
    p = sub.add_parser("record", help="Start recording a workflow")
    p.add_argument("name", type=str, help="Workflow name")

    # replay
    p = sub.add_parser("replay", help="Replay a recorded workflow")
    p.add_argument("name", type=str, help="Workflow name")

    # automate
    p = sub.add_parser("automate", aliases=["auto"], help="Run an autonomous GUI task from natural language")
    p.add_argument("task", type=str, help="Natural language task description")
    p.add_argument("--max-steps", type=int, default=20, help="Max agent steps")

    args = parser.parse_args()

    dispatch = {
        "screenshot": cmd_screenshot, "ss": cmd_screenshot,
        "read": cmd_read,
        "find": cmd_find,
        "click": cmd_click,
        "type": cmd_type,
        "record": cmd_record,
        "replay": cmd_replay,
        "automate": cmd_automate, "auto": cmd_automate,
    }

    asyncio.run(dispatch[args.command](args))


if __name__ == "__main__":
    main()
