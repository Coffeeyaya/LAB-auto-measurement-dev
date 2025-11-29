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
    on_coord = get_coord(grid, channel, "on")
    for i in range(len(channel_arr)):
        channel = channel_arr[i]
        wavelength = wavelength_arr[i]
        power = power_percentage_arr[i]
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

def time_dependent_power(conn, grid, channel, power_values, on_time=10, off_time=60):
    global laser_state
    laser_state = "power"
    conn.send("power")
    
    for power in power_values:
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

def single_on_off(conn, grid, channel, power, on_time=10, off_time=30):
    global laser_state
    laser_state = "1_on_off"
    conn.send("1_on_off")

    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)

    change_power_function(grid, channel, power)
    time.sleep(1)
    
    # turn on
    move_and_click(on_coord)
    time.sleep(on_time)

    # turn off
    move_and_click(on_coord)
    time.sleep(off_time)

    laser_state = "DONE"
    conn.send("DONE")

def multi_on_off(conn, grid, channel, power, on_time=1, off_time=1, peaks_num=20):
    global laser_state
    laser_state = "multi_on_off"
    conn.send("multi_on_off")

    on_coord = get_coord(grid, channel, "on")
    time.sleep(1)

    change_power_function(grid, channel, power)
    time.sleep(1)
    
    for i in range(peaks_num):
        move_and_click(on_coord)
        time.sleep(on_time)

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
    wavelength = str(row['wavelength_arr'])
    power_percentage = str(row['power_percentage_arr'])
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

        if cmd in ["ON", "OFF"] and laser_state != cmd:
            channel = 6
            power = "17" ### adjust this based on power measured
            change_power_function(grid, channel, power)
            time.sleep(1)
            on_coord = get_coord(grid, channel, "on")
            time.sleep(1)
            move_and_click(on_coord)
            time.sleep(0.5)
            laser_state = cmd
            conn.send(cmd)
        elif cmd == "1_on_off" and laser_state != "1_on_off":
            channel = 6
            power = "17"
            single_on_off(conn, grid, channel, power, on_time=1, off_time=1)
        elif cmd == "multi_on_off" and laser_state != "multi_on_off":
            channel = 6
            power = "17"
            multi_on_off(conn, grid, channel, power, on_time=1, off_time=1, peaks_num=3)
        elif cmd == "wavelength" and laser_state != "wavelength":
            time_dependent_wavelength(conn, grid, channel_arr, wavelength_arr, power_percentage_arr, on_time=1, off_time=10)
        elif cmd == "power" and laser_state != "power":
            channel = 6
            power_values = ["30.5", "22.5", "16.8", "12.5", "9.3", "6.8", "5.3"] ### adjust this based on power measured
            time_dependent_power(conn, grid, channel, power_values, on_time=1, off_time=1)
        elif cmd == "test" and laser_state != "test":
            channel = 6
            wavelength_power_arr = [("450", "115"), ("488", "77"), ("514", "34.4"), ("532", "33"),
                                     ("600", "25.5"), ("633", "20.2"), ("660", "17"), ("680", "17")] ### adjust this based on power measured
            time_dependent_wavelength(conn, grid, channel, wavelength_power_arr, on_time=1, off_time=3)    
    conn.close()
finally:
    server_socket.close()