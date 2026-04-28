"""
GUI Automator Agent — Computer Use Agent powered by GPT-4o Vision.

GPT-4o SEES the actual screen via screenshots and decides exactly where to click.
Captures each monitor separately for clear, readable images on multi-monitor setups.
"""
import json
import os
import subprocess
import base64
import asyncio
from io import BytesIO

async def run(state, **kwargs):
    task = kwargs.get("task")
    max_steps = kwargs.get("max_steps", 20)

    if not task:
        return {"result": "failed", "error": "Task description is required"}

    # --- Load API key ---
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    for env_path in [
        os.path.join(os.getcwd(), ".env"),
        "/home/ubuntu/neurocomputer/.env",
        os.path.join(os.path.dirname(__file__), "../../.env"),
    ]:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # --- Screenshot helpers ---
    def get_monitors():
        import mss
        with mss.MSS() as sct:
            return sct.monitors  # 0=combined, 1+=individual

    def capture_monitor(monitor_index):
        """Capture a single monitor. Returns (PIL Image, monitor_dict, base64_jpg).
        Sends at full resolution with a light coordinate grid for precision."""
        import mss
        from PIL import Image, ImageDraw, ImageFont

        with mss.MSS() as sct:
            monitors = sct.monitors
            mon = monitors[monitor_index]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # Draw a subtle coordinate grid every 200px
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for x in range(0, w, 200):
            draw.line([(x, 0), (x, h)], fill=(255, 0, 0, 60), width=1)
            draw.text((x + 2, 2), str(x), fill=(255, 0, 0))
        for y in range(0, h, 200):
            draw.line([(0, y), (w, y)], fill=(255, 0, 0, 60), width=1)
            draw.text((2, y + 2), str(y), fill=(255, 0, 0))

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=75)
        b64 = base64.b64encode(buf.getvalue()).decode()

        return img, mon, b64

    def take_screenshots():
        """Capture all individual monitors. Returns list of (img, mon, b64, index)."""
        monitors = get_monitors()
        results = []
        for i in range(1, len(monitors)):  # skip 0 (combined)
            img, mon, b64 = capture_monitor(i)
            results.append((img, mon, b64, i))
        return results

    # --- Action executor via xdotool ---
    def _xdotool(*args):
        my_env = os.environ.copy()
        if "DISPLAY" not in my_env:
            my_env["DISPLAY"] = ":1"
        result = subprocess.run(["xdotool", *args], capture_output=True, text=True, env=my_env)
        return result.stdout.strip()

    async def execute_action(action, screenshots):
        """Execute an action. screenshots = list of (img, mon, b64, index)."""
        action_type = action.get("action")

        # Determine which monitor to use for coordinate mapping
        mon_idx = action.get("monitor", 1)  # default to monitor 1
        # Find the matching screenshot
        target = None
        for img, mon, b64, idx in screenshots:
            if idx == mon_idx:
                target = (img, mon)
                break
        if target is None:
            target = (screenshots[0][0], screenshots[0][1])

        img, mon = target
        img_w, img_h = img.size
        mon_w, mon_h = mon["width"], mon["height"]
        mon_left, mon_top = mon.get("left", 0), mon.get("top", 0)

        if action_type == "click":
            rx, ry = action.get("x", 0), action.get("y", 0)
            abs_x = int(rx * mon_w / img_w) + mon_left
            abs_y = int(ry * mon_h / img_h) + mon_top
            print(f"   🖱️  Click: monitor {mon_idx} screenshot({rx},{ry}) → absolute({abs_x},{abs_y})")
            _xdotool("mousemove", str(abs_x), str(abs_y))
            await asyncio.sleep(0.05)
            _xdotool("click", "1")
            return f"Clicked at absolute ({abs_x}, {abs_y}) on monitor {mon_idx}"

        elif action_type == "double_click":
            rx, ry = action.get("x", 0), action.get("y", 0)
            abs_x = int(rx * mon_w / img_w) + mon_left
            abs_y = int(ry * mon_h / img_h) + mon_top
            print(f"   🖱️  DoubleClick: monitor {mon_idx} ({rx},{ry}) → absolute({abs_x},{abs_y})")
            _xdotool("mousemove", str(abs_x), str(abs_y))
            await asyncio.sleep(0.05)
            _xdotool("click", "--repeat", "2", "1")
            return f"Double-clicked at ({abs_x}, {abs_y}) on monitor {mon_idx}"

        elif action_type == "type":
            text = action.get("text", "")
            print(f"   ⌨️  Type: '{text}'")
            _xdotool("type", "--clearmodifiers", "--delay", "30", text)
            return f"Typed: {text}"

        elif action_type == "key":
            key = action.get("key", "")
            print(f"   ⌨️  Key: {key}")
            key_map = {"enter": "Return", "backspace": "BackSpace", "tab": "Tab", "escape": "Escape"}
            actual = key_map.get(key.lower(), key)
            _xdotool("key", "--clearmodifiers", actual)
            return f"Pressed key: {key}"

        elif action_type == "scroll":
            direction = action.get("direction", "down")
            amount = action.get("amount", 3)
            btn = "4" if direction == "up" else "5"
            print(f"   🖱️  Scroll {direction} x{amount}")
            _xdotool("click", "--repeat", str(amount), btn)
            return f"Scrolled {direction} {amount} clicks"

        elif action_type == "wait":
            secs = action.get("seconds", 2)
            print(f"   ⏳ Waiting {secs}s...")
            await asyncio.sleep(secs)
            return f"Waited {secs} seconds"

        elif action_type == "done":
            return "DONE"

        else:
            return f"Unknown action: {action_type}"

    # --- Detect monitor layout ---
    monitors = get_monitors()
    num_monitors = len(monitors) - 1  # subtract combined
    monitor_desc = ""
    for i in range(1, len(monitors)):
        m = monitors[i]
        monitor_desc += f"  - Monitor {i}: {m['width']}x{m['height']} at position left={m.get('left',0)}, top={m.get('top',0)}"
        if m.get('is_primary'):
            monitor_desc += " (PRIMARY)"
        if m.get('name'):
            monitor_desc += f" [{m['name']}]"
        monitor_desc += "\n"

    # --- System prompt ---
    system_prompt = f"""You are an autonomous Computer Use Agent controlling an Ubuntu Linux desktop.
Your task: {task}

## Desktop Layout
This desktop has {num_monitors} monitors:
{monitor_desc}
You will receive a SEPARATE screenshot for each monitor, labelled "Monitor 1", "Monitor 2", etc.

## How it works
- After EVERY action, you receive NEW screenshots of ALL monitors.
- You can SEE exactly what is on each monitor.
- Specify pixel coordinates ON THE SCREENSHOT IMAGE of the target monitor.
- You MUST include "monitor": N to indicate which monitor's screenshot your coordinates refer to.

## Available actions (respond with ONLY a JSON object):

{{"action": "click", "monitor": 1, "x": 640, "y": 400}}
  Click at pixel (x, y) on monitor N's screenshot.

{{"action": "double_click", "monitor": 1, "x": 100, "y": 50}}
  Double-click. Use for opening desktop icons.

{{"action": "type", "text": "youtube.com"}}
  Type text at the current cursor position. Click a field first!

{{"action": "key", "key": "Return"}}
  Press a key. Common: Return, Tab, Escape, BackSpace, ctrl+l, ctrl+t, alt+F4, super

{{"action": "scroll", "direction": "down", "amount": 3}}
  Scroll up or down.

{{"action": "wait", "seconds": 3}}
  Wait for something to load.

{{"action": "done", "reason": "Task completed"}}
  When the task is finished.

## CRITICAL RULES:
1. LOOK at the screenshots carefully before every action.
2. The screenshot images are scaled to ~1280px wide. Coordinates are pixels on THAT image.
3. ALWAYS specify "monitor": N for click/double_click actions.
4. To open an app, find its icon on the taskbar/desktop and click or double_click it.
5. To type in a browser address bar: press ctrl+l first (to focus it), then type.
6. After clicking/launching, use wait then check the new screenshots.
7. Be PRECISE with coordinates. Look at exactly where the element center is.
8. Output ONLY valid JSON, nothing else."""

    # --- Main agent loop ---
    history = [{"role": "system", "content": system_prompt}]
    steps_taken = []

    for i in range(max_steps):
        print(f"\n{'='*50}")
        print(f"--- Step {i+1}/{max_steps} ---")

        # Take screenshots of all monitors
        screenshots = take_screenshots()

        # Build multi-image message
        content_parts = []
        for img, mon, b64, idx in screenshots:
            w, h = img.size
            print(f"📸 Monitor {idx}: {w}x{h} (actual: {mon['width']}x{mon['height']}, left={mon.get('left',0)})")
            content_parts.append({
                "type": "text",
                "text": f"[Monitor {idx} screenshot — {w}x{h} pixels, actual resolution {mon['width']}x{mon['height']}]"
            })
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}
            })

        prev_result = f" Previous action result: {steps_taken[-1]['result']}" if steps_taken else ""
        content_parts.append({
            "type": "text",
            "text": f"What is your next action?{prev_result}"
        })

        history.append({"role": "user", "content": content_parts})

        # Ask GPT-4o with vision
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=history,
                temperature=0.1,
                max_tokens=300,
            )
            response_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ API error: {e}")
            steps_taken.append({"step": i+1, "action": "api_error", "result": str(e)})
            break

        history.append({"role": "assistant", "content": response_text})
        print(f"🤖 Agent: {response_text}")

        # Parse JSON
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            decision = json.loads(response_text[json_start:json_end])
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
            steps_taken.append({"step": i+1, "action": "parse_error", "result": str(e)})
            continue

        action_type = decision.get("action", "done")

        if action_type == "done":
            print(f"✅ Agent done: {decision.get('reason', '')}")
            steps_taken.append({"step": i+1, "action": "done", "result": decision.get("reason", "")})
            break

        # Execute
        print(f"⚡ Executing: {action_type}")
        try:
            result_str = await execute_action(decision, screenshots)
            print(f"📋 Result: {result_str}")
        except Exception as e:
            result_str = f"Error: {str(e)}"
            print(f"❌ {result_str}")

        steps_taken.append({"step": i+1, "action": action_type, "result": result_str})

        # Keep history manageable — images are expensive
        if len(history) > 14:
            history = [history[0]] + history[-12:]

    return {
        "result": "success" if steps_taken and steps_taken[-1]["action"] == "done" else "max_steps_reached",
        "steps_taken": steps_taken
    }
