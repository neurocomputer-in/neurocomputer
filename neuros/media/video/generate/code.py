import os
import sys
import threading
import uuid
from pathlib import Path

# When run as a neuro, we can't rely on __file__, so we need to find the repo root differently
# Assuming Infinity is always run from the repo root
repo_root = Path(os.getcwd())

# Ensure that “lib” is on Python’s import path.  If your working directory is the repo root,
# this will let us import lib/video_gen without installing it as a package.
if str(repo_root) not in sys.path:
    sys.path.append(str(repo_root))

try:
    from lib.video_gen.v_gen import InfinityVideoPipeline
except ImportError:
    # If the import still fails, it usually means lib/video_gen is missing __init__.py
    raise ImportError("Could not find lib.video_gen.v_gen. Make sure lib/video_gen exists and has __init__.py")

# Create a dictionary to store video generation status and results
video_tasks = {}

def generate_video_in_thread(task_id, topic, duration, slug=None):
    """Execute video generation in a separate thread"""
    try:
        pipeline = InfinityVideoPipeline()
        video_tasks[task_id]['status'] = 'generating'
        
        # This is where the long-running video generation happens
        video_path = pipeline.run(topic, duration, slug=slug)
        
        # Update the task with success result
        video_tasks[task_id]['status'] = 'completed'
        video_tasks[task_id]['result'] = str(video_path)
    except Exception as e:
        # Handle any errors
        video_tasks[task_id]['status'] = 'failed'
        video_tasks[task_id]['error'] = str(e)

async def run(state, *, topic: str = None, duration: int = 60):
    """
    topic: the text prompt for the video (string)
    duration: approximate length in seconds (int)
    """
    if topic is None:
        return {"reply": "⚠️  No topic provided.", "video_path": None}

    # Create a unique task ID for this video generation request
    task_id = uuid.uuid4().hex
    
    # Initialize the task in our tracking dictionary
    video_tasks[task_id] = {
        'status': 'starting',
        'topic': topic,
        'duration': duration,
        'result': None,
        'error': None
    }
    
    # Start the video generation in a separate thread
    thread = threading.Thread(
        target=generate_video_in_thread,
        args=(task_id, topic, duration),
        daemon=True  # Make the thread a daemon so it doesn't block process exit
    )
    thread.start()
    
    # Immediately return to the user with the task ID
    return {
        "reply": f"🎬 Video generation started! Your video on '{topic}' is being created in the background.\n\n" +
                 f"This may take a few minutes. You can continue using Infinity while this runs.\n\n" +
                 f"Task ID: `{task_id}`\n\n" +
                 f"To check status, ask: 'What's the status of my video task {task_id[:8]}?'",
        "video_task_id": task_id
    }

async def check_status(state, *, task_id: str = None):
    """
    Check the status of a video generation task
    task_id: the ID of the task to check (string)
    """
    if task_id is None:
        return {"reply": "⚠️ No task ID provided. Please provide the task ID you want to check."}
    
    # Find tasks starting with the provided ID (to allow for partial IDs)
    matching_tasks = []
    for full_id in video_tasks:
        if full_id.startswith(task_id):
            matching_tasks.append((full_id, video_tasks[full_id]))
    
    if not matching_tasks:
        return {"reply": f"⚠️ No video task found with ID starting with '{task_id}'"}
    
    if len(matching_tasks) > 1:
        # Multiple matches found, list them all
        task_list = "\n".join([f"- `{t[0][:8]}...`: {t[1]['topic']} ({t[1]['status']})" for t in matching_tasks])
        return {"reply": f"Found multiple matching tasks:\n{task_list}\n\nPlease specify which task ID you want to check."}
    
    # We have exactly one matching task
    task_id, task = matching_tasks[0]
    
    # Generate appropriate response based on status
    if task['status'] == 'starting':
        return {"reply": f"Your video on '{task['topic']}' is initializing..."}
    
    elif task['status'] == 'generating':
        return {"reply": f"Your video on '{task['topic']}' is currently being generated. This may take several minutes."}
    
    elif task['status'] == 'completed':
        video_path = task['result']
        return {
            "reply": f"✅ Your video is ready!\n\nTopic: '{task['topic']}'\nPath: ```\n{video_path}\n```",
            "video_path": video_path
        }
    
    elif task['status'] == 'failed':
        error = task['error']
        return {"reply": f"⚠️ Video generation failed for '{task['topic']}'\nError: {error}"}
    
    else:
        return {"reply": f"Unknown status '{task['status']}' for task {task_id}"}

