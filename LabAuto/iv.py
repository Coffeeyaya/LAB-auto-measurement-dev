import pygetwindow as gw
import pyautogui
import pyperclip
import re
import time
from LabAuto.network import Connection
from PIL import ImageGrab
from LabAuto.check_state import wait_for_cursor_idle

SCROLL_POSITION = [1700, 500]
SETTINGS_BOTTON = [360, 160]
GRAPH_BOTTON = [500, 160]

# for idvd
DRAIN_PANEL = [800, 300]
DRAIN_MODE = [1100, 310]
DRAIN_DUAL_SWEEP = [1044, 350]
DRAIN_START = [1350, 370] # same as gate start
DRAIN_STOP = [1350, 430] # same as gate stop
DRIAN_VG_VALUE = [1420, 360]

# for idvg
GATE_PANEL = [800, 500]
GATE_MODE = [1100, 310]
GATE_DUAL_SWEEP = [1044, 350]
GATE_START = [1350, 370]
GATE_STOP = [1350, 430]
GATE_VD_VALUE = [1420, 360]

#run & save
RUN_BOTTON = [325, 1000]
EXPORT_BOTTON = [970, 990]
PATH_BOTTON = [650, 610]
STOP_BOTTON = [390, 1000]

EIDT_PATH_POSITION = [777, 59]
OTHER_POSITION = [1596, 308]
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
    time.sleep(0.5)
    pyautogui.click(*coord)

def move_and_double_click(coord):
    pyautogui.moveTo(*coord)
    time.sleep(1)
    pyautogui.doubleClick(*coord)

def scroll_to_bottom():
    move_and_click(SCROLL_POSITION)
    for i in range(15):
        pyautogui.scroll(-500)

def fill_box_ctrl_a(content):
    pyperclip.copy(content)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press('enter')

def fill_box_no_ctrl_a(content):
    pyperclip.copy(content)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press('enter')


def change_vg_range(low, high):
    '''
    for idvg
    low: vg start (str)
    high: vg end (str)
    '''
    move_and_click(SETTINGS_BOTTON)
    time.sleep(2)
    scroll_to_bottom()

    move_and_click(GATE_PANEL)
    wait_for_cursor_idle()
    move_and_click(GATE_START)
    fill_box_ctrl_a(low)
    wait_for_cursor_idle()
    scroll_to_bottom()
    time.sleep(1)

    move_and_click(GATE_PANEL)
    wait_for_cursor_idle()
    move_and_click(GATE_STOP)
    fill_box_ctrl_a(high)
    wait_for_cursor_idle()
    scroll_to_bottom()


def change_vd_range(low, high):
    '''
    for idvd
    low: vd start (str)
    high: vd end (str)
    '''
    move_and_click(SETTINGS_BOTTON)
    time.sleep(2)
    scroll_to_bottom()

    move_and_click(DRAIN_PANEL)
    wait_for_cursor_idle()
    move_and_click(DRAIN_START)
    fill_box_ctrl_a(low)
    wait_for_cursor_idle()
    scroll_to_bottom()
    time.sleep(1)

    move_and_click(DRAIN_PANEL)
    wait_for_cursor_idle()
    move_and_click(DRAIN_STOP)
    fill_box_ctrl_a(high)
    wait_for_cursor_idle()
    scroll_to_bottom()

def change_idvd_vg_level(voltage): # change vg value for idvd
    '''
    voltage: voltage value (str)
    '''
    move_and_click(SETTINGS_BOTTON)
    time.sleep(2)
    scroll_to_bottom()
    move_and_click(GATE_PANEL)
    scroll_to_bottom()
    move_and_click(DRIAN_VG_VALUE)

    fill_box_ctrl_a(voltage)
    wait_for_cursor_idle()
    scroll_to_bottom()

def change_idvg_vd_level(voltage): # change vd value for idvg
    '''
    voltage: voltage value (str)
    '''
    move_and_click(SETTINGS_BOTTON)
    time.sleep(2)
    scroll_to_bottom()
    move_and_click(DRAIN_PANEL)
    scroll_to_bottom()
    move_and_click(GATE_VD_VALUE)

    fill_box_ctrl_a(voltage)
    wait_for_cursor_idle()
    scroll_to_bottom()

def watch_pixel(x=RUN_BOTTON[0], y=RUN_BOTTON[1], tol=10):
    """
    Monitors the color of a pixel at (x,y).
    Prints when the color changes beyond the tolerance.
    
    x, y : pixel coordinates
    tol  : tolerance (0 = exact match)
    """
    prev_color = None

    while True:
        screenshot = ImageGrab.grab()
        color = screenshot.getpixel((x, y))  # (R, G, B)

        if prev_color is not None:
            # Compare with tolerance
            if any(abs(c1 - c2) > tol for c1, c2 in zip(color, prev_color)):
                print(f"Color changed! {prev_color} -> {color}")
                break

        prev_color = color
        time.sleep(0.5)  # adjust speed as needed
def click_RUN():
    move_and_double_click(RUN_BOTTON)
    wait_for_cursor_idle()
    time.sleep(1)
    move_and_double_click(GRAPH_BOTTON)

def run_measurement(): # will detect color change, block if not change
    click_RUN()
    time.sleep(1)
    watch_pixel()

def click_STOP():
    move_and_double_click(STOP_BOTTON)
    time.sleep(3)

def export_data(folder_path, file_name):
    move_and_click(EXPORT_BOTTON)
    wait_for_cursor_idle()
    move_and_click(PATH_BOTTON)
    wait_for_cursor_idle()
    while not get_window(r'選擇'):
        time.sleep(1)
    move_and_click(EIDT_PATH_POSITION)
    fill_box_ctrl_a(folder_path)
    move_and_click(SELECT_FOLDER_BOTTON)
    wait_for_cursor_idle()
    move_and_click(FILE_NAME_BOTTON)
    fill_box_ctrl_a(file_name)
    move_and_click(EXPORT_SELECTED_RUN_BOTTON)
    print(f'STEP: export data to {folder_path}/{file_name}')
    wait_for_cursor_idle()
    
CHANGE_MEAS_MODE_BOTTON = [415, 65]
SAVE_PROJ_BOTTON = [890, 580]
PROJECT_FOLDER_BOTTON = [898, 66]
KICK_START_FILE_BOTTON = [654, 143]

def change_measurement_mode(meas_mode_path):
    move_and_click(CHANGE_MEAS_MODE_BOTTON)
    time.sleep(5)
    move_and_click(SAVE_PROJ_BOTTON) # save project window, won't show every time
    while not get_window(r'Open File'):
        time.sleep(1)
    time.sleep(1)
    move_and_click(PROJECT_FOLDER_BOTTON)
    fill_box_ctrl_a(meas_mode_path)
    time.sleep(1)
    move_and_double_click(KICK_START_FILE_BOTTON)
    time.sleep(5)
    

def filename_generator(material, device_number, measurement_type, condition):
    return rf'{material}_{measurement_type}_{device_number}_{condition}'

def illuminate_and_run(conn: Connection, wait_time=30):
    """
    Turn on illumination, wait, run measurement, then turn off.
    """
    print('STEP: illuminate_and_run()')

    # Send ON and wait for acknowledgment
    conn.send_json({"cmd": "ON"})
    conn.wait_for("ON")

    time.sleep(wait_time)  
    run_measurement()      

    # Turn OFF and wait for acknowledgment
    conn.send_json({"cmd": "OFF"})
    conn.wait_for("OFF")


def time_dependent_illumination_run(conn: Connection, wait_time=60):
    print('STEP: time dependent illuminate and run()')
    click_RUN()
    time.sleep(wait_time)
    conn.send_json({"cmd": "FUNCTION"})
    conn.wait_for("FUNCTION_DONE")
    time.sleep(wait_time)
    click_STOP()

def time_dependent_dark_current():
    print('STEP: time dependent dark current()')
    click_RUN()
    time.sleep(60)
    click_STOP()