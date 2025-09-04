import socket
import pyautogui, time
import numpy as np
from utils.laser_utils import init_AOTF, get_coord, change_power_function
from utils.socket_utils import send_cmd, receive_msg, wait_for, create_server, accept_client


laser_state = "OFF"

def time_dependent_wavelength(conn, grid):
    global laser_state
    laser_state = "FUNCTION"
    send_cmd(conn, "FUNCTION")

    # here, assume all power percentages are pre-setted
    channels = np.linspace(0, 7, 2, dtype=int)
    power_values = np.array(["50", "15"])
    
    for channel, power in zip(channels, power_values):
        on_coord = get_coord(grid, channel, "on")
        change_power_function(grid, channel, power)
        # turn on
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(1)

        # turn off
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(1)

    laser_state = "FUNCTION_DONE"
    send_cmd(conn, "FUNCTION_DONE")

def time_dependent(conn, grid, channel, power):
    global laser_state
    laser_state = "FUNCTION"
    send_cmd(conn, "FUNCTION")

    change_power_function(grid, channel, power)
    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)
    for i in range(3):
        print("ON")
        # turn on
        pyautogui.moveTo(*on_coord)
        time.sleep(0.1)
        pyautogui.click(*on_coord)
        time.sleep(0.9)

        # turn off
        print("OFF")
        pyautogui.moveTo(*on_coord)
        time.sleep(0.1)
        pyautogui.click(*on_coord)
        time.sleep(0.9)

    laser_state = "FUNCTION_DONE"
    send_cmd(conn, "FUNCTION_DONE")

grid = init_AOTF()
channel = 5
on_coord = get_coord(grid, channel, "on")

server_socket = create_server(host="0.0.0.0", port=5000)
conn, addr = accept_client(server_socket)

while True:
    try:
        cmd = receive_msg(conn)
        time.sleep(1)
    except ConnectionError:
        print("Client disconnected.")
        break

    if cmd == "ON" and laser_state != "ON":
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(0.5)
        laser_state = "ON"
        send_cmd(conn, "ON")

    elif cmd == "OFF" and laser_state != "OFF":
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(0.5)
        laser_state = "OFF"
        send_cmd(conn, "OFF")

    elif cmd == "FUNCTION" and laser_state != "FUNCTION":
        # time_dependent_wavelength(conn, grid)  # multi-channel FUNCTION
        time_dependent(conn, grid, channel=5, power="80")  # single-channel FUNCTION

conn.close()
server_socket.close()