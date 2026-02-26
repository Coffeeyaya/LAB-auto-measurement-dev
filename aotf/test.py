import numpy as np
import win32gui
import win32con
import win32api
import time

import pygetwindow as gw
import pyperclip
import pyautogui


# popup power slider.vi
# popup wavelength slider.vi

### background functions
def background_click(hwnd, x, y):
    """Sends an invisible left click to the window at relative x, y."""
    lparam = win32api.MAKELONG(int(x), int(y))
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam) # use PostMessage instead of SendMessage
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def background_double_click(hwnd, x, y):
    """
    Uses PostMessage instead of SendMessage to prevent the script 
    from hanging when a modal popup opens.
    """
    lparam = win32api.MAKELONG(int(x), int(y))
    # PostMessage returns immediately, so Python doesn't get stuck
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def background_paste(hwnd, text):
    """
    Copies text to clipboard and sends a background Paste command 
    directly to the window handle.
    """
    # 1. Put the new value on the clipboard
    pyperclip.copy(str(text))
    time.sleep(0.1)
    
    # modify this in the future so that it can paste without interfere
    # 2. Send the Paste message (WM_PASTE is 0x0302)
    # This is the "cleanest" way to paste in the background
    win32gui.PostMessage(hwnd, win32con.WM_PASTE, 0, 0)
    time.sleep(0.2)
    
    # 3. If WM_PASTE is ignored, we send the Ctrl+V keystrokes as a backup
    # VK_CONTROL = 0x11, 'V' = 0x56
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, ord('V'), 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, ord('V'), 0)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)
    
    # pyautogui.hotkey("ctrl", "v")
    # pyautogui.press('enter')
    print(f"Paste command for '{text}' sent.")


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

def get_active_popup_hwnd(title, timeout=3):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        # Check by specific title
        popup_hwnd = win32gui.FindWindow(None, title)
        
        if popup_hwnd != 0:
            print(f"Captured LabVIEW popup: {win32gui.GetWindowText(popup_hwnd)}")
            # Force it to (0,0) immediately to align with your grid math
            move_window_to_origin(popup_hwnd)
            return popup_hwnd
        
        time.sleep(0.1)
    
    print(f"Error: '{title}' did not appear.")
    return None

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
    # abs_x = power_coord[0] + 90 # 80
    # abs_y = power_coord[1] + 300 # 300
    abs_x = power_coord[0] + 75 # 80
    abs_y = power_coord[1] + 290 # 300
    return abs_x, abs_y

def get_power_ok_coord(power_coord):
    # abs_x = power_coord[0] + 90 # 80
    # abs_y = power_coord[1] + 335 # 330
    abs_x = power_coord[0] + 80 # 80
    abs_y = power_coord[1] + 325 # 330
    return abs_x, abs_y


def change_lambda(main_hwnd, grid, channel, new_lambda_value):
    lambda_x, lambda_y = grid[channel]["lambda"]
    background_click(main_hwnd, lambda_x, lambda_y)
    popup_hwnd = get_active_popup_hwnd('popup wavelength slider.vi') 
    window_title = win32gui.GetWindowText(popup_hwnd)
    print(f"Successfully captured popup window: '{window_title}'")
    
    if popup_hwnd == main_hwnd or popup_hwnd == 0:
        print("Error: Could not detect the popup window.")
        return
    
    popup_edit_x, popup_edit_y = get_lambda_edit_coord([0,0])
    move_window_to_origin(popup_hwnd)
    background_double_click(popup_hwnd, popup_edit_x, popup_edit_y)
    time.sleep(0.5)

    # hybrid_fill_box(popup_hwnd, new_lambda_value)
    
    # background_type(popup_hwnd, new_lambda_value)
    # time.sleep(0.5)

    background_paste(popup_hwnd, new_lambda_value) # works !
    time.sleep(0.5)
    
    popup_ok_x, popup_ok_y = get_lambda_ok_coord([0,0])
    background_click(popup_hwnd, popup_ok_x, popup_ok_y)
    time.sleep(0.5)


def change_power(main_hwnd, grid, channel, new_power_value):
    power_x, power_y = grid[channel]["power"]
    background_click(main_hwnd, power_x, power_y)
    popup_hwnd = get_active_popup_hwnd('popup power slider.vi')
    window_title = win32gui.GetWindowText(popup_hwnd)
    print(f"Successfully captured popup window: '{window_title}'")
    
    if popup_hwnd == main_hwnd or popup_hwnd == 0:
        print("Error: Could not detect the popup window.")
        return
    
    popup_edit_x, popup_edit_y = get_power_edit_coord([0,0])
    move_window_to_origin(popup_hwnd)
    background_double_click(popup_hwnd, popup_edit_x, popup_edit_y)
    time.sleep(0.5)

    background_paste(popup_hwnd, new_power_value) # works !
    time.sleep(1)
    
    popup_ok_x, popup_ok_y = get_power_ok_coord([0,0])
    background_click(popup_hwnd, popup_ok_x, popup_ok_y) # click or double click
    time.sleep(0.5)

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

        change_lambda(hwnd, grid, 2, "400")
        time.sleep(1)
        change_power(hwnd, grid, 2, "10")
        channel = 2
        on_coord = get_coord(grid, channel, "on")
        background_click(hwnd, on_coord[0], on_coord[1])