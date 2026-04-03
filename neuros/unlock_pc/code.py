
import subprocess
import os

async def run(state, **kwargs):
    """
    Unlocks the session using loginctl (systemd).
    """
    try:
        # 1. Find session ID
        # We look for a session belonging to the current user on seat0
        output = subprocess.check_output(["loginctl", "list-sessions", "--no-legend"], text=True)
        
        session_id = None
        current_user = os.environ.get("USER", "ubuntu")
        
        for line in output.strip().split('\n'):
            parts = line.split()
            # Typical format: 2 1000 ubuntu seat0 ...
            # We want the ID (index 0) where user (index 2) matches
            if len(parts) >= 3 and parts[2] == current_user:
                if "seat0" in line: # Prefer graphical seat
                    session_id = parts[0]
                    break
        
        if not session_id and output.strip():
             # Fallback: take the first one if we couldn't match strict criteria
             session_id = output.strip().split()[0]
             
        if not session_id:
            return {"reply": "⚠️ Could not find any active session to unlock."}

        # 2. Unlock
        cmd = ["loginctl", "unlock-session", session_id]
        subprocess.run(cmd, check=True)
        
        return {"reply": "🔓 Screen unlocked successfully."}
        
    except subprocess.CalledProcessError as e:
        return {"reply": f"⚠️ loginctl failed (permission/auth issue?): {e}"}
    except Exception as e:
        return {"reply": f"⚠️ Error: {e}"}
