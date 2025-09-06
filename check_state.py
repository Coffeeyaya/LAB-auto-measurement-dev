import time
import ctypes

# Windows API setup
user32 = ctypes.windll.user32
IDC_WAIT = 32514
IDC_APPSTARTING = 32650
standard_cursors = {
    "wait": user32.LoadCursorW(0, IDC_WAIT),
    "app_starting": user32.LoadCursorW(0, IDC_APPSTARTING),
}

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("hCursor", ctypes.c_void_p),
        ("ptScreenPos", POINT)
    ]

def get_current_cursor_handle():
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if user32.GetCursorInfo(ctypes.byref(ci)):
        return ci.hCursor
    return None

def is_cursor_loading():
    hcursor = get_current_cursor_handle()
    return hcursor in (standard_cursors["wait"], standard_cursors["app_starting"])

def wait_for_cursor_idle(timeout=30, check_interval=0.5):
    """
    Wait until the cursor becomes idle or timeout is reached.
    
    Parameters:
        timeout (float): Maximum seconds to wait.
        check_interval (float): Seconds between cursor checks.
    
    Returns:
        bool: True if cursor became idle, False if timeout reached.
    """
    start_time = time.time()
    while True:
        if not is_cursor_loading():
            return True
        if time.time() - start_time > timeout:
            return False
        time.sleep(check_interval)

# ---------------- Example Usage ----------------
if __name__ == "__main__":
    print("Waiting for cursor to become idle...")
    if wait_for_cursor_idle(timeout=15):
        print("Cursor is idle, safe to continue automation.")
    else:
        print("Timeout reached, cursor still loading.")
