import pyautogui
import time
from laser_utils import get_coord, get_lambda_edit_coord, get_lambda_ok_coord, \
    get_power_edit_coord, get_power_ok_coord, fill_box

def change_lambda_function(grid, channel, new_lambda_value):
    '''
    channel: int, AOTF output channels (0 ~ 7)
    new_lambda_value: str, the new wavelength value (400 ~ 700)
    '''
    lambda_coord = get_coord(grid, channel, "lambda")
    pyautogui.moveTo(*lambda_coord)
    time.sleep(0.5)
    pyautogui.click(*lambda_coord)

    lambda_edit_coord = get_lambda_edit_coord(lambda_coord)
    pyautogui.moveTo(*lambda_edit_coord)
    time.sleep(0.5)
    pyautogui.doubleClick(*lambda_edit_coord)
    time.sleep(0.5)
    fill_box(new_lambda_value)

    lambda_ok_coord = get_lambda_ok_coord(lambda_coord)
    pyautogui.moveTo(*lambda_ok_coord)
    time.sleep(0.5)
    pyautogui.click(*lambda_ok_coord)

def change_power_function(grid, channel, new_power_value):
    '''
    channel: int, AOTF output channels (0 ~ 7)
    new_power_value: str, the new power value (0 ~ 100) %
    '''
    power_coord = get_coord(grid, channel, "power")
    pyautogui.moveTo(*power_coord)
    time.sleep(0.5)
    pyautogui.click(*power_coord)

    power_edit_coord = get_power_edit_coord(power_coord)
    pyautogui.moveTo(*power_edit_coord)
    time.sleep(0.5)
    pyautogui.doubleClick(*power_edit_coord)
    time.sleep(0.5)
    fill_box(new_power_value)

    power_ok_coord = get_power_ok_coord(power_coord)
    pyautogui.moveTo(*power_ok_coord)
    time.sleep(0.5)
    pyautogui.click(*power_ok_coord)

