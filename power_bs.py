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

    laser.send_cmd({"channel": channel, "wavelength": wavelength, "power": mid, "on": 1}, wait_for_reply=True)
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
            "Measured Power (W)": power_table
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
            "Measured Power (W)": power_table
        })

        return measured_table

    finally:
        print('power meter closed')
        pm.close_meter()

if __name__ == "__main__":
    LIGHT_IP = "192.168.50.17" #
    print("Connecting to Laser PC...")
    laser = LaserController(LIGHT_IP, 5001)
    print("Laser connected.")
    

    with open(Path("config") / "power_config.json", "r") as f:
        parameters = json.load(f)
    wavelength_arr = np.array([450, 488, 514, 532, 600, 633, 660, 690])
    channel_arr = np.linspace(0, 7, 8).astype(int).astype(str) ### 
    # wavelength_arr = np.array([450, 532, 660])
    # channel_arr = np.array([0, 3, 6]).astype(int).astype(str) ### 
    power_arr = np.array([10, 20, 30]).astype(int).astype(str)

    os.makedirs("calibration", exist_ok=True)
    mode = parameters["mode"]
    if mode == "single_power_multi_wavelength":
        target_power = int(parameters["target_power"]) *  1e-9 # the unit in power_config.json is nW
        measured_table = single_power_multi_wavelength(laser, channel_arr, wavelength_arr, target_power)
        measured_table.to_csv(Path("calibration") / "single_power_multi_wavelength.csv", index=False)

    if mode == "multi_power_single_wavelength":
        target_wavelength = parameters["target_wavelength"]
        target_channel = parameters["target_channel"]
        measured_table = multi_power_single_wavelength(laser, power_arr, target_channel, target_wavelength)
        measured_table.to_csv(Path("calibration") / "multi_power_single_wavelength.csv", index=False)
    laser.close()