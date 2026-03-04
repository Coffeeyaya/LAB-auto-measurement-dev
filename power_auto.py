from LabAuto.network import Connection #
from pm.power import PowerMeter
import matplotlib.pyplot as plt
import numpy as np

LIGHT_IP = "192.168.50.17" #

conn = Connection.connect(LIGHT_IP, 5001)
conn.send_json({"channel": 6, "wavelength": "660"})
conn.receive_json() # Wait for confirmation

wavelength=660
average_count=10
measure_interval=0.2
num_points=10

pp_values = np.linspace(10, 50, 5)
p_arr = []
pm = PowerMeter()
try:
    pm.config_meter(wavelength, average_count)
    pm.zero_sensor()
    for pp in pp_values:
        conn.send_json({"channel": 6, "power": pp, "on": 1})
        conn.receive_json() # Wait for confirmation

        t, p = pm.measure_power(measure_interval=0.2, num_points=10)
        p_arr.append(p)
        conn.send_json({"channel": 6, "on": 1})
        conn.receive_json() # Wait for confirmation

    plt.figure()
    for p in p_arr:
        plt.plot(t, p)
    plt.xlabel("Time (s)")
    plt.ylabel("Power (W)")
    plt.title("PM100D Power vs Time")
    plt.grid(True)
    plt.show()

finally:
    pm.close_meter()
