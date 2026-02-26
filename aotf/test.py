import numpy as np
import win32gui
import win32con
import win32api
import time

import pygetwindow as gw
import pyperclip
import pyautogui


### background functions
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

# def background_type(hwnd, text):
#     """Sends invisible keystrokes to the currently active text box."""
#     for char in str(text):
#         win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
#         time.sleep(0.05)
#     # Send 'Enter' key
#     win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
#     win32gui.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)


def background_type(hwnd, text):
    """A more aggressive typing function for stubborn LabVIEW popups."""
    # 1. Clear any existing text first (sending backspaces)
    for _ in range(10):
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_BACK, 0)
    
    # 2. Type the new value
    for char in str(text):
        win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
        time.sleep(0.05)
    
    # 3. Send the ENTER signal 3 different ways
    # Way A: The Character
    win32gui.SendMessage(hwnd, win32con.WM_CHAR, win32con.VK_RETURN, 0)
    # Way B: The Virtual Key Down/Up
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.05)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    
    print(f"Typed {text} and sent Enter signal.")
    
def move_window_to_origin(hwnd):
    """
    Grabs a window by its handle and forces it to screen coordinates (0, 0)
    while keeping its original width and height intact.
    """
    # 1. Get the current dimensions of the popup so we don't accidentally squish it
    rect = win32gui.GetWindowRect(hwnd)
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    
    # 2. Move the window to X=0, Y=0
    # The 'True' at the end tells Windows to redraw the window immediately
    win32gui.MoveWindow(hwnd, 0, 0, width, height, True)
    print("Popup successfully grabbed and moved to (0, 0).")

# def get_active_popup_hwnd_title(expected_title=None):
#     """
#     Finds the popup window. If the popup steals focus when it spawns, 
#     GetForegroundWindow() will grab it immediately.
#     """
#     time.sleep(0.2) # Give the OS a moment to render the popup
    
#     if expected_title:
#         popup_hwnd = win32gui.FindWindow(None, expected_title)
#     else:
#         # Fallback: Just grab whatever window just popped to the front
#         popup_hwnd = win32gui.GetForegroundWindow()
#     move_window_to_origin(popup_hwnd)
#     return popup_hwnd


def get_active_popup_hwnd(main_hwnd):
    """Waits for and captures the newly spawned popup window handle and title."""
    time.sleep(0.3) # Give the GUI time to generate the window [cite: 606]
    
    popup_hwnd = win32gui.GetForegroundWindow()
    
    # Get the title text of the captured window
    window_title = win32gui.GetWindowText(popup_hwnd)
    
    if popup_hwnd == main_hwnd or popup_hwnd == 0:
        print(f"Warning: No new popup detected. Current active window: '{window_title}'")
        return None
    
    print(f"Successfully captured popup window: '{window_title}'")
    return popup_hwnd

## relative coordinate to popup window
def get_lambda_edit_coord(lambda_coord):
    # abs_x = lambda_coord[0] + 370 
    # abs_y = lambda_coord[1] + 40 
    abs_x = lambda_coord[0] + 350 # 350
    abs_y = lambda_coord[1] + 30 # 30
    return abs_x, abs_y

def get_lambda_ok_coord(lambda_coord):
    # abs_x = lambda_coord[0] + 440
    # abs_y = lambda_coord[1] + 40
    abs_x = lambda_coord[0] + 430
    abs_y = lambda_coord[1] + 30
    return abs_x, abs_y

def get_power_edit_coord(power_coord):
    abs_x = power_coord[0] + 90
    abs_y = power_coord[1] + 300
    return abs_x, abs_y

def get_power_ok_coord(power_coord):
    abs_x = power_coord[0] + 90
    abs_y = power_coord[1] + 335
    return abs_x, abs_y


def change_lambda(main_hwnd, grid, channel, new_lambda_value):
    lambda_x, lambda_y = grid[channel]["lambda"]
    background_click(main_hwnd, lambda_x, lambda_y)
    popup_hwnd = get_active_popup_hwnd(main_hwnd) 
    window_title = win32gui.GetWindowText(popup_hwnd)
    print(f"Successfully captured popup window: '{window_title}'")
    
    if popup_hwnd == main_hwnd or popup_hwnd == 0:
        print("Error: Could not detect the popup window.")
        return
    
    popup_edit_x, popup_edit_y = get_lambda_edit_coord([0,0])
    move_window_to_origin(popup_hwnd)
    background_double_click(popup_hwnd, popup_edit_x, popup_edit_y)
    time.sleep(0.5)
    
    # background_type(popup_hwnd, new_lambda_value)
    # time.sleep(0.5)
    
    # popup_ok_x, popup_ok_y = get_lambda_ok_coord([0,0])
    # background_click(popup_hwnd, popup_ok_x, popup_ok_y)
    # time.sleep(0.5)

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

if __name__ == "__main__":
    grid = init_AOTF_grid()
    hwnd = win32gui.FindWindow(None, "AOTF Controller")

    if hwnd == 0:
        print("Please open the AOTF Controller GUI first.")
    else:
        # channel = 2
        # on_coord = get_coord(grid, channel, "on")
        # background_click(hwnd, on_coord[0], on_coord[1])

        change_lambda(hwnd, grid, 2, "500")