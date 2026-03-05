from LabAuto.network import Connection #
from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LIGHT_IP = "192.168.50.17" #

conn = Connection.connect(LIGHT_IP, 5001)
conn.send_json({"channel": 6, "wavelength": "660"})
conn.receive_json() # Wait for confirmation

average_count=10
measure_interval=0.2
num_points=10

pp_values = np.linspace(10, 100, 10) # pp = power percent
wavelength_arr = np.array([450, 488, 514, 532, 600, 633, 660, 690])

n_wl = len(wavelength_arr)
n_pp = len(pp_values)
power_arr = np.zeros((n_wl, n_pp, num_points)) # 3D array

pm = PowerMeter()
try:
    pm.zero_sensor() # zero power meter
    for i, wavelength in enumerate(wavelength_arr):
        pm.config_meter(wavelength, average_count) # change power meter wavelength

        for j, pp in enumerate(pp_values):
            conn.send_json({"channel": i, "power": pp, "on": 1})
            conn.receive_json() # Wait for confirmation (blocked until recv)

            t, p = pm.measure_power(measure_interval=0.2, num_points=10) # t,p are 2 1D arrays. t are the same for different measurement
            
            power_arr[i, j, :] = p #

            conn.send_json({"channel": 6, "on": 1})
            conn.receive_json() # Wait for confirmation
    ### raw data
    raw_data = {
        "wavelengths": wavelength_arr, # shape (8,)
        "power_percent": pp_values,    # shape (10,)
        "power": power_arr             # shape (8, 10, num_points)
    }
    np.savez(
        "raw_power_data.npz",
        wavelengths=wavelength_arr,   # (8,)
        power_percent=pp_values,      # (10,)
        power=power_arr               # (8, 10, num_points)
    )
    '''
    later load it using:
    data = np.load("raw_data.npz")
    wavelengths = data["wavelengths"]
    power_percent = data["power_percent"]
    power_arr = data["power"]  # shape (8, 10, num_points)
    '''  

    ### stable data = mean of last 3 power values
    stable_power_data = {
        "wavelengths": wavelength_arr, # shape (8,)
        "power_percent": pp_values,    # shape (10,)
        "power": np.mean(power_arr[:, :, -3:], axis=2)   # shape (8, 10), take the mean of last 3 powers
    }
    
    df = pd.DataFrame(
        data=stable_power_data,
        index=wavelength_arr,  # row labels
        columns=pp_values      # column labels
    )

    df.to_csv("stable_power_table.csv")
    ### plot heat map
    '''
    import matplotlib.pyplot as plt
    import numpy as np

    # mean_power.shape == (n_wl, n_pp)
    # wavelength_arr.shape == (n_wl,)
    # pp_values.shape == (n_pp,)

    plt.figure(figsize=(8,6))

    # Use imshow for heatmap
    # Note: origin='lower' makes the first wavelength at bottom
    plt.imshow(
        mean_power, 
        aspect='auto', 
        origin='lower', 
        extent=[pp_values[0], pp_values[-1], wavelength_arr[0], wavelength_arr[-1]],
        cmap='viridis'  # or 'plasma', 'inferno', etc.
    )

    plt.colorbar(label='Measured Power (W)')
    plt.xlabel('Power Percent (%)')
    plt.ylabel('Wavelength (nm)')
    plt.title('Laser Power vs Wavelength and PP')
    plt.show()
    '''
    

finally:
    print('power meter closed')
    pm.close_meter()
