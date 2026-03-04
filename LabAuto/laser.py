import numpy as np
import pygetwindow as gw
import pyperclip
import pyautogui
import time

def init_AOTF():

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

def get_popup_window(window_title):
    while True:
        try:
            win = gw.getWindowsWithTitle(f"{window_title}")
            win = win[0]
            win.restore()
            win.moveTo(0, 0)
            win.activate()
            break
        except gw.PyGetWindowException:
            print(f'can not get window: {window_title}')

def move_and_click(coord):
    pyautogui.moveTo(*coord)
    time.sleep(0.1)
    pyautogui.click(*coord)

def get_coord(grid, channel, field):
    coord = grid[channel][field]
    return coord
    
def get_lambda_edit_coord(lambda_coord):
    abs_x = lambda_coord[0] + 350 
    abs_y = lambda_coord[1] + 30 
    return abs_x, abs_y

def get_lambda_ok_coord(lambda_coord):
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

def fill_box_no_ctrl_a(content):
    pyperclip.copy(content)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press('enter')

def change_lambda_function(grid, channel, new_lambda_value):
    '''
    channel: int, AOTF output channels (0 ~ 7)
    new_lambda_value: str, the new wavelength value (400 ~ 700)
    '''
    lambda_coord = get_coord(grid, channel, "lambda")
    pyautogui.moveTo(*lambda_coord)
    time.sleep(0.5)
    pyautogui.click(*lambda_coord)

    get_popup_window('popup wavelength slider.vi')
    time.sleep(0.5)

    lambda_edit_coord = get_lambda_edit_coord([0,0])
    pyautogui.moveTo(*lambda_edit_coord)
    time.sleep(0.5)
    
    pyautogui.doubleClick(*lambda_edit_coord)
    time.sleep(0.5)
    fill_box_no_ctrl_a(new_lambda_value)

    lambda_ok_coord = get_lambda_ok_coord([0,0])
    pyautogui.moveTo(*lambda_ok_coord)
    time.sleep(0.5)
    pyautogui.click(*lambda_ok_coord)
    time.sleep(0.5)# important

def change_power_function(grid, channel, new_power_value):
    '''
    channel: int, AOTF output channels (0 ~ 7)
    new_power_value: str, the new power value (0 ~ 100) %
    '''
    power_coord = get_coord(grid, channel, "power")
    pyautogui.moveTo(*power_coord)
    time.sleep(0.5)
    pyautogui.click(*power_coord)

    power_edit_coord = get_power_edit_coord([0,0])

    get_popup_window('popup power slider.vi')
    time.sleep(0.5)

    pyautogui.moveTo(*power_edit_coord)
    time.sleep(0.5)
    pyautogui.doubleClick(*power_edit_coord)
    time.sleep(0.5)
    fill_box_no_ctrl_a(new_power_value)

    power_ok_coord = get_power_ok_coord(power_coord)
    pyautogui.moveTo(*power_ok_coord)
    time.sleep(0.5)
    pyautogui.click(*power_ok_coord)
    time.sleep(0.5)# important

def press_on_button(grid, channel):
    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)
    move_and_click(on_coord)

if __name__ == "__main__":
    grid = init_AOTF()
    # change_lambda_function(grid, 0, "660")
    # change_power_function(grid, 0, "50")
    get_popup_window('popup power slider.vi')