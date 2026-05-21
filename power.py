from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import json
import os
import csv
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
                             tolerance=2 * 1e-9, 
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
        print(f'target power = {target_power * 1e+9:.3f} nW')
        laser.send_cmd({"channel": channel, "power": mid, "on": 1}, wait_for_reply=True)
        time.sleep(1)

        _, p = pm.measure_power(measure_interval, num_points) 
        measured_power = np.mean(p[-3:])   
        print(f'measured power = {measured_power * 1e+9:.3f} nW')
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

import csv
import os
import pandas as pd
import numpy as np

def multi_power_multi_wavelength(laser, channel_arr, wavelength_arr, power_arr, log_filename="calibration/incremental_log.csv"):

    n_wavelength = len(wavelength_arr)
    n_power = len(power_arr)

    pp_table = np.zeros((n_wavelength, n_power))
    power_table = np.zeros((n_wavelength, n_power))
    
    sorted_powers = sorted(power_arr)

    # =========================================================
    # 1. RESUME LOGIC: Load previously completed measurements
    # =========================================================
    completed_data = {}
    if os.path.exists(log_filename):
        try:
            df_log = pd.read_csv(log_filename)
            for _, row in df_log.iterrows():
                # Cast to float to ensure matching works perfectly (e.g., 660 == 660.0)
                wl = float(row["Wavelength (nm)"])
                tgt_p = float(row["Target Power (nW)"])
                completed_data[(wl, tgt_p)] = (row["PP"], row["Measured Power (nW)"])
            print(f"Resuming measurement: Found {len(completed_data)} previously saved points.")
        except Exception as e:
            print(f"Could not read existing log (starting fresh): {e}")

    # Create directory and write header ONLY if the file doesn't exist
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    file_exists = os.path.exists(log_filename)
    
    with open(log_filename, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(log_filename) == 0:
            writer.writerow(["Wavelength (nm)", "Target Power (nW)", "PP", "Measured Power (nW)"])

        pm = PowerMeter() # Initialize PowerMeter once
        try:
            pm.zero_sensor() 
            for i, wavelength in enumerate(wavelength_arr):
                current_pp_min = 1 
                
                for j, target_p_nw in enumerate(sorted_powers):
                    
                    # =========================================================
                    # 2. CHECK CACHE: Skip physical measurement if already done
                    # =========================================================
                    if (float(wavelength), float(target_p_nw)) in completed_data:
                        pp, measured_power_nw = completed_data[(float(wavelength), float(target_p_nw))]
                        print(f"Skipping {wavelength}nm at {target_p_nw}nW (Loaded from log).")
                        
                        # Populate final matrices with cached data
                        pp_table[i, j] = pp
                        power_table[i, j] = measured_power_nw
                        
                        # Crucial: Keep updating current_pp_min so the optimization still works!
                        current_pp_min = pp 
                        continue 
                    
                    # =========================================================
                    # 3. MEASURE: Only triggers if not in the log
                    # =========================================================
                    target_power = target_p_nw * 1e-9
                    channel = str(channel_arr[i]) 
                    
                    pp, measured_power = find_pp_for_target_power(
                        laser=laser, pm=pm, channel=channel, target_power=target_power, 
                        wavelength=wavelength, pp_min=current_pp_min, pp_max=150
                    )
                    
                    if pp is not None:
                        current_pp_min = pp 
                    
                    pp_table[i, j] = pp
                    power_table[i, j] = measured_power * 1e+9

                    # Append new data point immediately
                    writer.writerow([wavelength, target_p_nw, pp, measured_power * 1e+9])
                    f.flush() # Force write to hard drive immediately to prevent data loss on crash

            # Generate final DataFrames
            measured_power_df = pd.DataFrame(
                power_table, index=wavelength_arr, columns=sorted_powers
            )
            pp_df = pd.DataFrame(
                pp_table, index=wavelength_arr, columns=sorted_powers
            )

            measured_power_df.index.name = "Wavelength (nm)"
            measured_power_df.columns.name = "Target Power (nW)"
            pp_df.index.name = "Wavelength (nm)"
            pp_df.columns.name = "Target Power (nW)"

            return pp_df, measured_power_df

        finally:
            print('Power meter closed.')
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