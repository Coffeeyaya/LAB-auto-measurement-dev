import numpy as np
import pygetwindow as gw
import pyperclip
import pyautogui

def init_AOTF():
    win = gw.getWindowsWithTitle("AOTF Controller")[0]
    win.moveTo(0, 0)
    win.activate()

    x = np.array([200, 270, 320])-10
    y = np.linspace(190, 430, 8)

    fields = ["lambda", "power", "on"]

    grid = {i: {} for i in range(len(y))}

    for i, row_y in enumerate(y):
        for j, col_x in enumerate(x):
            grid[i][fields[j]] = (col_x, row_y)
    return grid


def get_coord(grid, channel, field):
    coord = grid[channel][field]
    return coord
    
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
    abs_y = power_coord[1] + 340
    return abs_x, abs_y

def fill_box(content):
    pyperclip.copy(content)
    # pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press('enter')
