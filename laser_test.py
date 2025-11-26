import time
import numpy as np
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click, change_lambda_function
from LabAuto.network import create_server, Connection
import pandas as pd

laser_state = "OFF"

def time_dependent_wavelength(conn, grid, channel, wavelength_power_arr, on_time=3, off_time=3):
    global laser_state
    laser_state = "wavelength"
    conn.send("wavelength")
    on_coord = get_coord(grid, channel, "on")
    for wavelength, power in wavelength_power_arr:
        change_lambda_function(grid, channel, wavelength)
        change_power_function(grid, channel, power)
        # turn on
        move_and_click(on_coord)
        time.sleep(on_time)

        # turn off
        move_and_click(on_coord)
        time.sleep(off_time)

    laser_state = "DONE"
    conn.send("DONE")

# def set_wavelength_power(grid, channel):
#     global laser_state
#     on_coord = get_coord(grid, channel, "on")
#     for wavelength, power in wavelength_power_arr:
#         change_lambda_function(grid, channel, wavelength)
#         change_power_function(grid, channel, power)
#         # turn on
#         move_and_click(on_coord)

grid = init_AOTF()
server_socket = create_server("0.0.0.0", 5001)
conn, addr = Connection.accept(server_socket)

df = pd.read_csv("wavelength_power.csv")
wavelength_power_arr = []
for index, row in df.iterrows():
    wavelength = row['wavelength_arr']
    power_percent = int(row['power_percentage_arr'])
    wavelength_power_arr.append((wavelength, power_percent))
# wavelength_power_arr = [("450", "115"), ("488", "77"), ("514", "34.4"), ("532", "33"),
#                         ("600", "25.5"), ("633", "20.2"), ("660", "17"), ("680", "17")] ### adjust this based on power measured

try:
    while True:
        try:
            cmd = conn.receive()
            time.sleep(1)
        except ConnectionError:
            print("Client disconnected.")
            break # break only the inner loop

        if cmd == "set":
            pass
        elif cmd == "test" and laser_state != "test":
            channel = 6
            time_dependent_wavelength(conn, grid, channel, wavelength_power_arr, on_time=3, off_time=3)    
    conn.close()
finally:
    server_socket.close()