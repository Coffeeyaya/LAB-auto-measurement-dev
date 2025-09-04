import pygetwindow as gw
import pyautogui
import pyperclip
import re
import time

SCROLL_POSITION = [1700, 500]

# for idvd
DRAIN_PANEL = [800, 300]
DRAIN_MODE = [1100, 310]
DRAIN_DUAL_SWEEP = [1044, 350]
DRAIN_START = [1350, 370]
DRAIN_STOP = [1350, 430]
DRIAN_VG_VALUE = [1420, 360]

# for idvg
GATE_PANEL = [800, 500]
GATE_MODE = [1100, 310]
GATE_DUAL_SWEEP = [1044, 350]
GATE_START = [1350, 370]
GATE_STOP = [1350, 430]

#run & save
RUN_BOTTON = [325, 1000]
EXPORT_BOTTON = [950, 990]
PATH_BOTTON = [650, 610]
STOP_BOTTON = [390, 1000]


# EIDT_PATH_POSITION = [1270, 235]
EIDT_PATH_POSITION = [777, 59]
OTHER_POSITION = [1596, 308]
# SELECT_FOLDER_BOTTON = [1375, 820]
SELECT_FOLDER_BOTTON = [897, 641]

FILE_NAME_BOTTON = [760, 660]
EXPORT_SELECTED_RUN_BOTTON = [890, 890]


def get_window(pattern):
    windows = gw.getAllWindows()  # get all windows
    matched_windows = [w for w in windows if re.search(pattern, w.title, re.IGNORECASE)]
    try:
        win = matched_windows[0]
        win.moveTo(0, 0)
        win.activate()
        return True
    except:
        print('window closed')
        return False

def move_and_click(coord):
    pyautogui.moveTo(*coord)
    time.sleep(1)
    pyautogui.click(*coord)

def move_and_double_click(coord):
    pyautogui.moveTo(*coord)
    time.sleep(1)
    pyautogui.doubleClick(*coord)

def scroll_to_bottom():
    move_and_click(SCROLL_POSITION)
    for i in range(10):
        pyautogui.scroll(-500)

def fill_box_ctrl_a(content):
    pyperclip.copy(content)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press('enter')

def fill_box_no_ctrl_a(content):
    pyperclip.copy(content)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press('enter')


# def change_vg_range(low, high):
#     '''
#     for idvd
#     low: vg start (str)
#     high: vg end (str)
#     '''
#     move_and_click(DRAIN_PANEL)

#     move_and_click(DRAIN_START)
#     fill_box(low)
#     scroll_to_bottom()

#     move_and_click(DRAIN_STOP)
#     fill_box(high)
#     scroll_to_bottom()

def change_idvd_vg_level(voltage): # change vg value for idvd
    '''
    voltage: voltage value (str)
    '''
    move_and_click(GATE_PANEL)
    move_and_click(DRIAN_VG_VALUE)

    fill_box_ctrl_a(voltage)
    scroll_to_bottom()

def run_measurement():
    move_and_click(RUN_BOTTON)
    time.sleep(10)

def stop_measurement():
    move_and_click(STOP_BOTTON)
    time.sleep(3)

def export_data(folder_path, file_name):
    move_and_click(EXPORT_BOTTON)
    move_and_click(PATH_BOTTON)
    time.sleep(1)

    get_window(r'選擇')
    move_and_click(EIDT_PATH_POSITION)
    fill_box_ctrl_a(folder_path)
    move_and_click(SELECT_FOLDER_BOTTON)

    get_window(r'Kick')
    move_and_click(FILE_NAME_BOTTON)
    fill_box_ctrl_a(file_name)
    move_and_click(EXPORT_SELECTED_RUN_BOTTON)
    print(f'save data to {folder_path}/{file_name}')
    
CHANGE_MEAS_MODE_BOTTON = [415, 65]
SAVE_PROJ_BOTTON = [890, 580]
PROJECT_FOLDER_BOTTON = [898, 66]
KICK_START_FILE_BOTTON = [654, 143]

def change_measurement_mode(meas_mode_path):
    move_and_click(CHANGE_MEAS_MODE_BOTTON)
    time.sleep(1)
    move_and_click(SAVE_PROJ_BOTTON)
    while not get_window(r'Open File'):
        time.sleep(3)
    move_and_click(PROJECT_FOLDER_BOTTON)
    fill_box_ctrl_a(meas_mode_path)
    time.sleep(1)
    move_and_double_click(KICK_START_FILE_BOTTON)
    time.sleep(5)
