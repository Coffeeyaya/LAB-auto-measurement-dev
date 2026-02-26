import numpy as np
import win32gui
import win32con
import win32api
import time

import pygetwindow as gw
import pyperclip
import pyautogui



import win32api
import win32gui
import win32con
import time

import win32gui
import win32con
import win32api
import time


   
def get_lambda_edit_coord(lambda_coord):
    abs_x = lambda_coord[0] + 370
    abs_y = lambda_coord[1] + 40
    return abs_x, abs_y

def get_lambda_ok_coord(lambda_coord):
    abs_x = lambda_coord[0] + 440
    abs_y = lambda_coord[1] + 40
    return abs_x, abs_y

def get_power_edit_coord(power_coord):
    abs_x = power_coord[0] + 90
    abs_y = power_coord[1] + 300
    return abs_x, abs_y

def get_power_ok_coord(power_coord):
    abs_x = power_coord[0] + 90
    abs_y = power_coord[1] + 335
    return abs_x, abs_y

def get_active_popup_hwnd(expected_title=None):
    """
    Finds the popup window. If the popup steals focus when it spawns, 
    GetForegroundWindow() will grab it immediately.
    """
    time.sleep(0.2) # Give the OS a moment to render the popup
    
    if expected_title:
        popup_hwnd = win32gui.FindWindow(None, expected_title)
    else:
        # Fallback: Just grab whatever window just popped to the front
        popup_hwnd = win32gui.GetForegroundWindow()
        
    return popup_hwnd

def change_lambda_truly_invisible(main_hwnd, grid, channel, new_lambda_value):
    # 1. Double click the main grid to spawn the popup
    lambda_x, lambda_y = grid[channel]["lambda"]
    background_double_click(main_hwnd, lambda_x, lambda_y)
    
    # 2. Dynamically find the popup that just appeared
    # NOTE: If the popup has a specific title (like "Edit" or "Value"), put it here.
    popup_hwnd = get_active_popup_hwnd() 
    
    if popup_hwnd == main_hwnd or popup_hwnd == 0:
        print("Error: Could not detect the popup window.")
        return
    
    popup_edit_x, popup_edit_y = get_lambda_edit_coord([0,0])
    
    background_click(popup_hwnd, popup_edit_x, popup_edit_y)
    time.sleep(0.1)
    
    # 4. Inject the text invisibly
    background_type(popup_hwnd, new_lambda_value)
    time.sleep(0.1)
    
    popup_ok_x, popup_ok_y = get_lambda_ok_coord([0,0])
    background_click(popup_hwnd, popup_ok_x, popup_ok_y)
    time.sleep(0.1)

def background_click(hwnd, x, y):
    """Sends an invisible left click to the window at relative x, y."""
    lparam = win32api.MAKELONG(int(x), int(y))
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def background_double_click(hwnd, x, y):
    """Sends an invisible double click."""
    lparam = win32api.MAKELONG(int(x), int(y))
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def background_type(hwnd, text):
    """Sends invisible keystrokes to the currently active text box."""
    for char in str(text):
        win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
        time.sleep(0.01)
    # Send 'Enter' key
    win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    win32gui.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

# --- 2. Your Grid Logic (Unchanged) ---

def init_AOTF_grid():
    while True:
        try:
            win = gw.getWindowsWithTitle("AOTF Controller")
            win = win[0]
            win.restore()
            win.moveTo(0, 0)
            win.activate()
            break
        except gw.PyGetWindowException:
            pyautogui.click(win.left, win.top)

    x = np.array([190, 270, 320])
    y = np.linspace(193, 430, 8)
    fields = ["lambda", "power", "on"]
    grid = {i: {} for i in range(len(y))}

    for i, row_y in enumerate(y):
        for j, col_x in enumerate(x):
            grid[i][fields[j]] = (col_x, row_y)
    return grid


def get_coord(grid, channel, field):
    coord = grid[channel][field]
    return coord
# --- 3. The Upgraded Function ---

def change_lambda_background(hwnd, grid, channel, new_lambda_value):
    '''
    channel: int, AOTF output channels (0 ~ 7)
    new_lambda_value: str, the new wavelength value (400 ~ 700)
    '''
    # 1. Click the main lambda box
    lambda_x, lambda_y = grid[channel]["lambda"]
    background_click(hwnd, lambda_x, lambda_y)
    time.sleep(0.5)

    # 2. Double click the edit box (using your offsets)
    edit_x, edit_y = lambda_x + 370, lambda_y + 40
    background_double_click(hwnd, edit_x, edit_y)
    time.sleep(0.5)

    # 3. Type the new value and press Enter invisibly
    background_type(hwnd, new_lambda_value)
    time.sleep(0.5)

    # 4. Click OK (using your offsets)
    ok_x, ok_y = lambda_x + 440, lambda_y + 40
    background_click(hwnd, ok_x, ok_y)
    time.sleep(0.5)

if __name__ == "__main__":
    grid = init_AOTF_grid()
    hwnd = win32gui.FindWindow(None, "AOTF Controller")

    if hwnd == 0:
        print("Please open the AOTF Controller GUI first.")
    else:
        
        # channel = 2
        # on_coord = get_coord(grid, channel, "on")
        # background_click(hwnd, on_coord[0], on_coord[1])

        change_lambda_truly_invisible(hwnd, grid, 2, 500)