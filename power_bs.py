from LabAuto.network import Connection #
from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time

def find_pp_for_target_power(conn,
                             pm,
                             channel,
                             target_power,
                             wavelength,
                             average_count=10,
                             measure_interval=0.2,
                             num_points=5,
                             pp_min=5, ##
                             pp_max=120, ##
                             tolerance=3 * 1e-9,
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

if __name__ == "__main__":
    LIGHT_IP = "192.168.50.17" #
    conn = Connection.connect(LIGHT_IP, 5001)
    # conn.send_json({"channel": 6, "wavelength": "660"})
    # conn.receive_json() # Wait for confirmation

    average_count=10
    measure_interval=0.2
    num_points=10

    # pp_values = np.linspace(10, 100, 10) # pp = power percent
    # wavelength_arr = np.array([450, 488, 514, 532, 600, 633, 660, 690])
    # channel_arr = np.linspace(0, 7, 8).astype(str) ### 
    wavelength_arr = np.array([450])
    channel_arr = np.array([0]).astype(str) ###
    

    pm = PowerMeter()

    n_wl = len(wavelength_arr)
    pp_table = np.zeros(n_wl)
    power_table = np.zeros(n_wl)

    try:
        pm.zero_sensor() # zero power meter
        for i, wavelength in enumerate(wavelength_arr):
            pp, power = find_pp_for_target_power(conn=conn, pm=pm, channel=int(channel_arr[i]), target_power=100 * 1e-9, wavelength=wavelength,
                                    pp_min = 5, pp_max = 120)
            pp_table[i] = pp
            power_table[i] = power
            
        measured_table = pd.DataFrame({
            "Wavelength (nm)": wavelength_arr,
            "PP (%)": pp_table,
            "Measured Power (W)": power_table
        })

        measured_table.to_csv("wavelength_pp_power.csv", index=False)

    finally:
        print('power meter closed')
        pm.close_meter()