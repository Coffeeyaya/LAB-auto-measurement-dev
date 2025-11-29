import time
import numpy as np
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click, change_lambda_function
from LabAuto.network import create_server, Connection
import pandas as pd

laser_state = "OFF"

def time_dependent_wavelength(conn, grid, channel_arr, wavelength_arr, power_percentage_arr, on_time=10, off_time=10):
    global laser_state
    laser_state = "wavelength"
    conn.send("wavelength")
    for i in range(len(channel_arr)):
        channel = channel_arr[i]
        wavelength = wavelength_arr[i]
        power = power_percentage_arr[i]
        on_coord = get_coord(grid, channel, "on")
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


grid = init_AOTF()
server_socket = create_server("0.0.0.0", 5001)
conn, addr = Connection.accept(server_socket)

df = pd.read_csv("wavelength_power.csv")
channel_arr = []
wavelength_arr = []
power_percentage_arr = []
for index, row in df.iterrows():
    wavelength = row['wavelength_arr']
    power_percentage = row['power_percentage_arr']
    channel = int(row['channel'])
    channel_arr.append(channel)
    wavelength_arr.append(wavelength)
    power_percentage_arr.append(power_percentage)

try:
    while True:
        try:
            cmd = conn.receive()
            time.sleep(1)
        except ConnectionError:
            print("Client disconnected.")
            break # break only the inner loop
        if  cmd == "test" and laser_state != "test":
            time_dependent_wavelength(conn, grid, channel_arr, wavelength_arr, power_percentage_arr, on_time=10, off_time=10)    
    conn.close()
finally:
    server_socket.close()