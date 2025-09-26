import time
import numpy as np
from utils.laser_utils import init_AOTF, get_coord, change_power_function, move_and_click
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client


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
        move_and_click(on_coord)
        time.sleep(0.9)

        # turn off
        move_and_click(on_coord)
        time.sleep(0.9)

    laser_state = "FUNCTION_DONE"
    send_cmd(conn, "FUNCTION_DONE")

def time_dependent(conn, grid, channel, power, on_time=1, off_time=2, num_peaks=10):
    global laser_state
    laser_state = "FUNCTION"
    send_cmd(conn, "FUNCTION")

    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)

    change_power_function(grid, channel, power)
    time.sleep(10)

    for i in range(num_peaks):
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord)
        time.sleep(off_time)

    time.sleep(60)    
    for i in range(num_peaks):
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord * 2)
        time.sleep(off_time)

    time.sleep(60)    
    for i in range(num_peaks):
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord * 4)
        time.sleep(off_time)

    laser_state = "FUNCTION_DONE"
    send_cmd(conn, "FUNCTION_DONE")



grid = init_AOTF()
server_socket = create_server(host="0.0.0.0", port=5001)
try: 
    while True:    
        conn, addr = accept_client(server_socket)
        while True:
            try:
                cmd = receive_msg(conn)
                time.sleep(1)
            except ConnectionError:
                print("Client disconnected.")
                break # break only the inner loop

            if cmd in ["ON", "OFF"] and laser_state != cmd:
                channel = 6
                power = "15"
                change_power_function(grid, channel, power)
                time.sleep(1)
                on_coord = get_coord(grid, channel, "on")
                time.sleep(1)
                move_and_click(on_coord)
                time.sleep(0.5)
                laser_state = cmd
                send_cmd(conn, cmd)

            elif cmd == "FUNCTION" and laser_state != "FUNCTION":
                # time_dependent_wavelength(conn, grid)  # multi-channel FUNCTION
                time_dependent(conn, grid, channel=6, power="15", num_peaks=10)  # single-channel FUNCTION

        conn.close()
finally:
    server_socket.close()