import time
import numpy as np
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click
from LabAuto.network import create_server, Connection


laser_state = "OFF"

def time_dependent_wavelength(conn, grid, channels, power_values, on_time=10, off_time=60):
    global laser_state
    laser_state = "wavelength"
    conn.send("wavelength")
    
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

def time_dependent(conn, grid, channel, power, on_time=10, off_time=30):
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
            power = "17.2" ### adjust this based on power measured
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
            power = "17.2"
            time_dependent(conn, grid, channel, power, on_time=10, off_time=30)
        elif cmd == "wavelength" and laser_state != "wavelength":
            channels = np.arange(0, 8, 1, dtype=int)
            power_values = ["100", "73", "34.5", "33.5", "25.5", "20.3", "17.2", "17"] ### adjust this based on power measured
            time_dependent_wavelength(conn, grid, channels, power_values, on_time=1, off_time=1)
        elif cmd == "power" and laser_state != "power":
            channel = 6
            power_values = ["30.5", "22.5", "16.8", "12.5", "9.3", "6.8", "5.3"] ### adjust this based on power measured
            time_dependent_power(conn, grid, channel, power_values, on_time=1, off_time=1)
    conn.close()
finally:
    server_socket.close()