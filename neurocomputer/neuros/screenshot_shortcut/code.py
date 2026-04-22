async def run(state, *args, **kwargs):
    import ctypes
    import time

    # Define key codes
    VK_SNAPSHOT = 0x2C
    VK_LWIN = 0x5B

    # Load user32.dll
    user32 = ctypes.windll.user32

    # Simulate key press
    user32.keybd_event(VK_LWIN, 0, 0, 0)  # Press Windows key
    user32.keybd_event(VK_SNAPSHOT, 0, 0, 0)  # Press Print Screen key
    time.sleep(0.1)  # Short delay
    user32.keybd_event(VK_SNAPSHOT, 0, 2, 0)  # Release Print Screen key
    user32.keybd_event(VK_LWIN, 0, 2, 0)  # Release Windows key

    return {}