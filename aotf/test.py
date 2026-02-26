import numpy as np
import win32gui
import win32con
import win32api
import time

import pygetwindow as gw
import pyperclip
import pyautogui

# --- 1. The Win32 API Toolset ---

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
        # change_lambda_background(hwnd, grid, channel=2, new_lambda_value="670")
        channel = 2
        on_coord = get_coord(grid, channel, "on")