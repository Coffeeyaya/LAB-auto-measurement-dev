from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import json
import os
from pathlib import Path
from LabAuto.laser_remote import LaserController


def find_pp_for_target_power(laser,
                             pm,
                             channel,
                             target_power,
                             wavelength,
                             average_count=10,
                             measure_interval=0.2,
                             num_points=10,
                             pp_min=1, 
                             pp_max=150, 
                             tolerance=3 * 1e-9, 
                             max_iter=10):
    
    pm.config_meter(wavelength, average_count)

    low = pp_min
    high = pp_max

    best_pp = None
    measured_power = None
    channel = str(channel) 
    
    laser.send_cmd({"channel": channel, "wavelength": wavelength}, wait_for_reply=True)
    time.sleep(1)

    for _ in range(max_iter):
        
        mid = (low + high) / 2 

        laser.send_cmd({"channel": channel, "power": mid, "on": 1}, wait_for_reply=True)
        time.sleep(1)

        _, p = pm.measure_power(measure_interval, num_points) 
        measured_power = np.mean(p[-3:])   

        if abs(measured_power - target_power) <= tolerance:
            best_pp = mid
            laser.send_cmd({"channel": channel, "on": 1}, wait_for_reply=True)
            time.sleep(1)
            break

        if measured_power > target_power:
            high = mid
        else:
            low = mid

        best_pp = mid

        laser.send_cmd({"channel": channel, "on": 1}, wait_for_reply=True)
        time.sleep(1)

    return best_pp, measured_power


def multi_power_multi_wavelength(laser, channel_arr, wavelength_arr, power_arr):

    n_wavelength = len(wavelength_arr)
    n_power = len(power_arr)

    pp_table = np.zeros((n_wavelength, n_power))
    power_table = np.zeros((n_wavelength, n_power))
    
    # --- MODIFIED: Sort powers ascending to allow dynamic bounding ---
    sorted_powers = sorted(power_arr)

    pm = PowerMeter()
    try:
        pm.zero_sensor() 
        for i, wavelength in enumerate(wavelength_arr):
            
            # Reset the minimum bound to 1 at the start of each new wavelength
            current_pp_min = 1 
            
            for j, target_p_nw in enumerate(sorted_powers):
                target_power = target_p_nw * 1e-9
                channel = str(channel_arr[i]) 
                
                # Pass the dynamic current_pp_min instead of a hardcoded 1
                pp, measured_power = find_pp_for_target_power(
                    laser=laser, pm=pm, channel=channel, target_power=target_power, 
                    wavelength=wavelength, pp_min=current_pp_min, pp_max=150
                )
                
                # --- OPTIMIZATION: Update the minimum bound for the next target power ---
                if pp is not None:
                    # We know the next power is higher, so it MUST require at least this PP
                    current_pp_min = pp 
                
                pp_table[i, j] = pp
                power_table[i, j] = measured_power

        measured_power_df = pd.DataFrame(
            power_table,                 
            index=wavelength_arr,       
            columns=sorted_powers       # Ensure columns match the sorted order
        )

        pp_df = pd.DataFrame(
            pp_table,                 
            index=wavelength_arr,       
            columns=sorted_powers       # Ensure columns match the sorted order
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
    LIGHT_IP = "10.0.0.2" 
    print("Connecting to Laser PC...")
    laser = LaserController(LIGHT_IP, 5001)
    print("Laser connected.")

    with open(Path("config") / "power_config.json", "r") as f:
        parameters = json.load(f)
        
    wavelength_arr = parameters["wavelength_arr"] 
    channel_arr = parameters["channel_arr"] 
    power_arr = parameters["power_arr"] 

    pp_df, measured_power_df = multi_power_multi_wavelength(laser, channel_arr, wavelength_arr, power_arr)
    
    os.makedirs("calibration", exist_ok=True)
    pp_df.to_csv(Path("calibration") / Path('pp_df.csv'), index=True)
    measured_power_df.to_csv(Path("calibration") / Path('measured_power_df.csv'), index=True)
    
    laser.close()
    print("Laser closed")