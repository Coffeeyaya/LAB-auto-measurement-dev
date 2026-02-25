import win32gui
import win32con
import win32api
import time

def click_window_background(window_title, x, y):
    """
    Sends a left mouse click to a specific window at the given (x, y) coordinates.
    The coordinates are relative to the top-left corner of the window itself.
    """
    # 1. Find the window by its exact title
    # Based on the manual, the title is likely "AOTF Controller"
    hwnd = win32gui.FindWindow(None, window_title)
    
    if hwnd == 0:
        print(f"Error: Could not find window named '{window_title}'")
        return

    # 2. Convert the X, Y coordinates into the binary format Windows expects
    lparam = win32api.MAKELONG(x, y)

    # 3. Send the "Mouse Down" message directly to the window
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    
    # 4. Tiny delay to simulate a human click duration
    time.sleep(0.05)
    
    # 5. Send the "Mouse Up" message
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
    print(f"Clicked {window_title} at relative coordinates ({x}, {y})")

# --- Example Usage ---
# You will need to find the exact X, Y coordinates of the text boxes or buttons
# relative to the top-left corner of the AOTF Controller window.
window_name = "AOTF Controller"

# Example: Click on the text box for Channel 1's wavelength
click_window_background(window_name, x=150, y=100)