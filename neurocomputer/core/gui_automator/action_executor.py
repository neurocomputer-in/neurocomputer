import asyncio
import subprocess
import time

def _xdotool(*args: str) -> str:
    """Run an xdotool command and return stdout."""
    result = subprocess.run(["xdotool", *args], capture_output=True, text=True)
    return result.stdout.strip()

class ActionExecutor:
    """Executes GUI actions using xdotool."""
    
    async def click(self, x: int, y: int, button: int = 1, repeat: int = 1):
        _xdotool("mousemove", str(x), str(y))
        await asyncio.sleep(0.05)
        args = ["click"]
        if repeat > 1:
            args.extend(["--repeat", str(repeat)])
        args.append(str(button))
        _xdotool(*args)
        
    async def right_click(self, x: int, y: int):
        await self.click(x, y, button=3)
        
    async def double_click(self, x: int, y: int):
        await self.click(x, y, repeat=2)
        
    async def type_text(self, text: str):
        _xdotool("type", "--delay", "50", text)
        
    async def press_key(self, key: str):
        # Map common keys to xdotool keys
        mapping = {
            "enter": "Return",
            "backspace": "BackSpace",
            "tab": "Tab",
            "escape": "Escape",
            "space": "space"
        }
        actual_key = mapping.get(key.lower(), key)
        _xdotool("key", actual_key)
        
    async def move_to(self, x: int, y: int):
        _xdotool("mousemove", str(x), str(y))
        
    async def drag_to(self, x1: int, y1: int, x2: int, y2: int, button: int = 1):
        _xdotool("mousemove", str(x1), str(y1))
        await asyncio.sleep(0.05)
        _xdotool("mousedown", str(button))
        await asyncio.sleep(0.05)
        _xdotool("mousemove", str(x2), str(y2))
        await asyncio.sleep(0.05)
        _xdotool("mouseup", str(button))
        
    async def scroll(self, direction: str, amount: int = 1):
        # xdotool scroll mapping: 4=up, 5=down
        btn = "4" if direction == "up" else "5"
        _xdotool("click", "--repeat", str(amount), btn)
