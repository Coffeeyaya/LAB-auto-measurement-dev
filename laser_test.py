import time
import numpy as np
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click
# from LabAuto.network import create_server, Connection


laser_state = "OFF"

def time_dependent_wavelength(grid, channels, power_values):
    global laser_state
    laser_state = "FUNCTION"
    
    for channel, power in zip(channels, power_values):
        on_coord = get_coord(grid, channel, "on")
        change_power_function(grid, channel, power)
        # turn on
        move_and_click(on_coord)
        time.sleep(2)

        # turn off
        move_and_click(on_coord)
        time.sleep(2)

    laser_state = "FUNCTION_DONE"

grid = init_AOTF()
if __name__ == "__main__":
    channels = np.arange(0, 7, 1, dtype=int)
    power_values = np.arange(10, 18, 1)
    power_values = power_values.astype(str)
    time_dependent_wavelength(grid, power_values)
