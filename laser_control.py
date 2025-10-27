import time
import numpy as np
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click
from LabAuto.network import create_server, Connection


laser_state = "OFF"

def time_dependent_wavelength(conn, grid, channels, power_values, on_time=10, off_time=60):
    global laser_state
    laser_state = "power"
    conn.send("power")
    
    for channel, power in zip(channels, power_values):
        on_coord = get_coord(grid, channel, "on")
        change_power_function(grid, channel, power)
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord)
        time.sleep(off_time)

    laser_state = "DONE"
    conn.send("DONE")

def time_dependent(conn, grid, channel, power, on_time=10, off_time=30, num_peaks=5):
    global laser_state
    laser_state = "multi_on_off"
    conn.send("multi_on_off")

    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)

    change_power_function(grid, channel, power)
    time.sleep(1)
    for i in range(num_peaks):
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord)
        time.sleep(off_time)

    laser_state = "DONE"
    conn.send("DONE")



grid = init_AOTF()
server_socket = create_server("0.0.0.0", 5001)
conn, addr = Connection.accept(server_socket)
try:   
    while True:
        try:
            cmd = conn.receive()
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
            conn.send(cmd)

        elif cmd == "power" and laser_state != "power":
            # time_dependent(conn, grid, channel=6, power="18.3", num_peaks=1)  # single-channel FUNCTION
            channels = np.arange(0, 8, 1, dtype=int)
            power_values = ["114", "85", "39", "39", "28", "21.5", "18.3", "18.2"]

            # reverse 
            # channels = channels[::-1]
            # power_values = power_values[::-1]
            time_dependent_wavelength(conn, grid, channels, power_values, on_time=10, off_time=30)
    conn.close()
finally:
    server_socket.close()