from LabAuto.network import Connection #
from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import json

def find_pp_for_target_power(conn,
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

    for _ in range(max_iter):

        mid = (low + high) / 2

        # Send power command
        conn.send_json({"channel": channel, "power": mid, "on": 1})
        conn.receive_json()
        time.sleep(1)

        # Measure power (average final value)
        _, p = pm.measure_power(measure_interval, num_points) # t,p
        measured_power = np.mean(p[-3:])   # average last 3 points

        # Check convergence
        if abs(measured_power - target_power) <= tolerance:
            best_pp = mid
            conn.send_json({"channel": channel, "on": 1})
            conn.receive_json()
            time.sleep(1)
            break

        if measured_power > target_power:
            high = mid     # too much power -> decrease
        else:
            low = mid      # too little power -> increase

        best_pp = mid

        conn.send_json({"channel": channel, "on": 1})
        conn.receive_json()
        time.sleep(1)

    return best_pp, measured_power

def single_power_multi_wavelength(conn, target_power):
    wavelength_arr = np.array([450, 488, 514, 532, 600, 633, 660, 690])
    channel_arr = np.linspace(0, 7, 8).astype(int).astype(str) ### 
    n_wl = len(wavelength_arr)
    pp_table = np.zeros(n_wl)
    power_table = np.zeros(n_wl)

    pm = PowerMeter()
    try:
        pm.zero_sensor() # zero power meter
        for i, wavelength in enumerate(wavelength_arr):
            pp, power = find_pp_for_target_power(conn=conn, pm=pm, channel=channel_arr[i], target_power=target_power, wavelength=wavelength,
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
    
def multi_power_single_wavelength(conn, target_channel, target_wavelength):
    power_arr = np.array([20, 40, 100, 300])

    n_power = len(power_arr)
    pp_table = np.zeros(n_power)
    power_table = np.zeros(n_power)

    pm = PowerMeter()
    try:
        pm.zero_sensor() # zero power meter
        for i, power in enumerate(power_arr):
            pp, power = find_pp_for_target_power(conn=conn, pm=pm, channel=target_channel, target_power=power, wavelength=target_wavelength,
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
    conn = Connection.connect(LIGHT_IP, 5001)

    with open("power_config.json", "r") as f:
        parameters = json.load(f)

    mode = parameters["mode"]
    if mode == "single_power_multi_wavelength":
        target_power = int(parameters["target_power"]) *  1e-9 # the unit in power_config.json is nW
        measured_table = single_power_multi_wavelength(conn, target_power)
        if measured_table:
            measured_table.to_csv("single_power_multi_wavelength.csv", index=False)

    if mode == "multi_power_single_wavelength":
        target_wavelength = parameters["target_wavelength"]
        target_channel = parameters["target_channel"]
        measured_table = multi_power_single_wavelength(conn, target_channel, target_wavelength)
        if measured_table:
            measured_table.to_csv("multi_power_single_wavelength.csv", index=False)

    