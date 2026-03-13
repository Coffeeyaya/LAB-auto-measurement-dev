from LabAuto.network import Connection #
from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import json
import os
from pathlib import Path
from laser_remote import LaserController


def find_pp_for_target_power(laser,
                             pm,
                             channel,
                             target_power,
                             wavelength,
                             average_count=10,
                             measure_interval=0.2,
                             num_points=10,
                             pp_min=1, ##
                             pp_max=150, ##
                             tolerance=3 * 1e-9, # if error < 3 nW, stop
                             max_iter=10):
    """
    Binary search to find power_percent that produces target optical power.

    Returns
    -------
    best_pp : float
    measured_power : float
    """
    pm.config_meter(wavelength, average_count)

    low = pp_min
    high = pp_max

    best_pp = None
    measured_power = None
    channel = str(channel) ###
    laser.send_cmd({"channel": channel, "wavelength": wavelength}, wait_for_reply=True)
    time.sleep(1)

    for _ in range(max_iter):

        mid = (low + high) / 2

        # Send power command
        laser.send_cmd({"channel": channel, "power": mid, "on": 1}, wait_for_reply=True)
        time.sleep(1)

        # Measure power (average final value)
        _, p = pm.measure_power(measure_interval, num_points) # t,p
        measured_power = np.mean(p[-3:])   # average last 3 points

        # Check convergence
        if abs(measured_power - target_power) <= tolerance:
            best_pp = mid
            laser.send_cmd({"channel": channel, "on": 1}, wait_for_reply=True)
            time.sleep(1)
            break

        if measured_power > target_power:
            high = mid     # too much power -> decrease
        else:
            low = mid      # too little power -> increase

        best_pp = mid

        laser.send_cmd({"channel": channel, "on": 1}, wait_for_reply=True)
        time.sleep(1)

    return best_pp, measured_power
'''
def single_power_multi_wavelength(laser, channel_arr, wavelength_arr, target_power):
    n_wl = len(wavelength_arr)
    pp_table = np.zeros(n_wl)
    power_table = np.zeros(n_wl)
    print(channel_arr)

    pm = PowerMeter()
    try:
        pm.zero_sensor() # zero power meter
        for i, wavelength in enumerate(wavelength_arr):
            pp, power = find_pp_for_target_power(laser=laser, pm=pm, channel=channel_arr[i], target_power=target_power, wavelength=wavelength,
                                    pp_min = 1, pp_max = 150)
            pp_table[i] = pp
            power_table[i] = power
            
        measured_table = pd.DataFrame({
            "Power (nW)": [target_power] * n_wl,
            "Channel": channel_arr,
            "Wavelength (nm)": wavelength_arr,
            "PP (%)": pp_table,
            "Measured Power (nW)": power_table * 1e+9
        })

        return measured_table
    finally:
        print('power meter closed')
        pm.close_meter()
    
def multi_power_single_wavelength(laser, target_channel, power_arr, target_wavelength):
    n_power = len(power_arr)
    pp_table = np.zeros(n_power)
    power_table = np.zeros(n_power)

    pm = PowerMeter()
    try:
        pm.zero_sensor() # zero power meter
        for i, power in enumerate(power_arr):
            pp, power = find_pp_for_target_power(laser=laser, pm=pm, channel=target_channel, target_power=power, wavelength=target_wavelength,
                                    pp_min = 1, pp_max = 150)
            pp_table[i] = pp
            power_table[i] = power
            
        measured_table = pd.DataFrame({
            "Wavelength (nm)": [target_wavelength] * n_power,
            "Channel": [target_channel] * n_power,
            "Power (nW)": power_arr,
            "PP (%)": pp_table,
            "Measured Power (nW)": power_table * 1e+9
        })

        return measured_table

    finally:
        print('power meter closed')
        pm.close_meter()
    '''

def multi_power_multi_wavelength(laser, channel_arr, wavelength_arr, power_arr):

    n_wavelength = len(wavelength_arr)
    n_power = len(power_arr)

    pp_table = np.zeros((n_wavelength, n_power))
    power_table = np.zeros((n_wavelength, n_power))

    pm = PowerMeter()
    try:
        pm.zero_sensor() # zero power meter
        for i, wavelength in enumerate(wavelength_arr):
            for j, target_power in enumerate(power_arr):
                target_power = target_power * 1e-9
                channel = str(channel_arr[i]) # channel is bind to wavelength, it's int
                pp, measured_power = find_pp_for_target_power(laser=laser, pm=pm, channel=channel, target_power=target_power, 
                                                     wavelength=wavelength, pp_min = 1, pp_max = 150)
                pp_table[i, j] = pp
                power_table[i, j] = measured_power

        measured_power_df = pd.DataFrame(
        power_table,                 
        index=wavelength_arr,       # rows
        columns=power_arr           # columns
        )

        pp_df = pd.DataFrame(
        pp_table,                 
        index=wavelength_arr,       # rows
        columns=power_arr           # columns
        )

        measured_power_df.index.name = "Wavelength (nm)"
        measured_power_df.columns.name = "Target Power (nW)"
        pp_df.index.name = "Wavelength (nm)"
        pp_df.columns.name = "Target Power (nW)"

        return pp_df, measured_power_df

    finally:
        print('power meter closed')
        pm.close_meter()

if __name__ == "__main__":
    LIGHT_IP = "10.0.0.2" # use ethernet cable
    print("Connecting to Laser PC...")
    laser = LaserController(LIGHT_IP, 5001)
    print("Laser connected.")

    with open(Path("config") / "power_config.json", "r") as f:
        parameters = json.load(f)
    wavelength_arr = parameters["wavelength_arr"] # int arr
    channel_arr = parameters["channel_arr"] # int arr
    power_arr = parameters["power_arr"] # int arr

    pp_df, measured_power_df = multi_power_multi_wavelength(laser, channel_arr, wavelength_arr, power_arr)
    os.makedirs("calibration", exist_ok=True)
    pp_df.to_csv(Path("calibration") / Path('pp_df.csv'), index=False)
    measured_power_df.to_csv(Path("calibration") / Path('measured_power_df.csv'), index=False)
    
    laser.close()
    print("Laser closed")