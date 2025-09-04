import socket
import pyautogui, time
import numpy as np
from change_lambda_power import change_power_function
from laser_utils import init_AOTF, get_coord
from socket_utils import send_cmd, receive_msg


laser_state = "OFF"

def time_dependent_wavelength(conn, grid):
    global laser_state
    laser_state = "FUNCTION"
    send_cmd(conn, "FUNCTION")

    # here, assume all power percentages are pre-setted
    channels = np.linspace(0, 7, 2, dtype=int)
    power_values = np.array(["50", "15"])

    grid = init_AOTF()
    on_coord = get_coord(grid, channel, "on")
    change_power_function(grid, channel, power)
    for channel, power in zip(channels, power_values):
        
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

# measurement settings
grid = init_AOTF()
channel = 5
on_coord = get_coord(grid, channel, "on")

# socket settings
HOST = "0.0.0.0"   # listen on all interfaces
PORT = 5000        # must match client

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print(f"Laser server listening on {HOST}:{PORT}...")
conn, addr = server_socket.accept()
print(f"Connected by {addr}")

while True:
    try:
        cmd = receive_msg(conn)
        time.sleep(1)
    except ConnectionError:
        print("Client disconnected.")
        break

    if cmd == "ON" and laser_state != "ON":
        '''
        use global settings for: grid, channel, on_coord
        '''
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(0.5)
        laser_state = "ON"
        send_cmd(conn, cmd)

    elif cmd == "OFF" and laser_state != "OFF":
        '''
        use global settings for: grid, channel, on_coord
        '''
        pyautogui.moveTo(*on_coord)
        time.sleep(0.2)
        pyautogui.click(*on_coord)
        time.sleep(0.5)
        laser_state = "OFF"
        send_cmd(conn, cmd)

    elif cmd == "FUNCTION" and laser_state != "FUNCTION":
        '''
        use local settings for: grid, channel, on_coord
        '''
        #  time_dependent_wavelength(conn, grid) # multiple wavelength, pre-set power
        time_dependent(conn, grid, channel=5, power="80") # typical single wavelength, single power

conn.close()
server_socket.close()
