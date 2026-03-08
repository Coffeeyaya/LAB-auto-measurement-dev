import win32gui
import win32api
import time

def log_relative_coordinates(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print("Window not found!")
        return

    print("Move your mouse to the target and hold for 2 seconds...")
    time.sleep(2) # Give yourself time to position the mouse
    
    # 1. Get global screen position
    global_x, global_y = win32api.GetCursorPos()
    
    # 2. Convert to client-relative coordinates
    client_x, client_y = win32gui.ScreenToClient(hwnd, (global_x, global_y))
    
    print(f"--- Coordinate Found ---")
    print(f"Global Screen Pos: {global_x}, {global_y}")
    print(f"Relative (Client) Pos: {client_x}, {client_y}")
    print(f"USE THESE IN YOUR SCRIPT: {client_x}, {client_y}")

# Run this while the AOTF Controller is open
log_relative_coordinates("AOTF Controller")