"""
OpenClaw Delegate Neuro

Executes tasks by delegating to the OpenClaw agent framework.
Supports both single requests and continuous conversation handoffs.
"""

import asyncio
import json
import subprocess
from typing import Optional

async def run(state, *, task: str, session_id: Optional[str] = None):
    """
    Delegate a task to OpenClaw agent.
    
    Args:
        task: The task/prompt to send to OpenClaw
        session_id: Optional session ID for continuous conversations
    
    Returns:
        dict with:
            - response: OpenClaw's response text
            - status: "success" or "error"
            - badge: "🦞" to identify OpenClaw responses
    """
    
    # Build openclaw command
    cmd = ["openclaw", "agent", "--message", task]
    
    # Add session management for continuous conversations
    if session_id:
        cmd.extend(["--session-id", session_id])
    
    # Add JSON output for easier parsing
    cmd.append("--json")
    
    try:
        # Execute OpenClaw command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )
        
        if result.returncode == 0:
            # Parse JSON response
            try:
                data = json.loads(result.stdout)
                
                # Extract text from standard OpenClaw generic response structure
                # Structure: { "result": { "payloads": [ { "text": "..." } ] } }
                response_text = None
                if "result" in data and "payloads" in data["result"]:
                    payloads = data["result"]["payloads"]
                    if isinstance(payloads, list) and len(payloads) > 0:
                        response_text = payloads[0].get("text")
                
                # Fallback if structure doesn't match
                if not response_text:
                    response_text = data.get("text", result.stdout)
                    
            except json.JSONDecodeError:
                # Fallback to raw output
                response_text = result.stdout.strip()
            
            return {
                "response": response_text,
                "status": "success",
                "badge": "🦞",
                "reply": f"🦞 **OpenClaw**: {response_text}"
            }
        else:
            error_msg = result.stderr.strip() or "OpenClaw command failed"
            return {
                "response": error_msg,
                "status": "error",
                "badge": "🦞",
                "reply": f"🦞 **OpenClaw Error**: {error_msg}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "response": "OpenClaw agent timed out",
            "status": "error",
            "badge": "🦞",
            "reply": "🦞 **OpenClaw Error**: Request timed out after 60 seconds"
        }
    except FileNotFoundError:
        return {
            "response": "OpenClaw not found. Please ensure it's installed.",
            "status": "error",
            "badge": "🦞",
            "reply": "🦞 **OpenClaw Error**: OpenClaw CLI not found. Please install it."
        }
    except Exception as e:
        return {
            "response": str(e),
            "status": "error",
            "badge": "🦞",
            "reply": f"🦞 **OpenClaw Error**: {str(e)}"
        }
