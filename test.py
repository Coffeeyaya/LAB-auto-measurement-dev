import numpy as np
import pandas as pd
import json
from pathlib import Path

with open(Path("config") / "power_config.json", "r") as f:
        parameters = json.load(f)
wavelength_arr = parameters["wavelength_arr"]
channel_arr = parameters["channel_arr"]
power_arr = parameters["power_arr"]
print(type(wavelength_arr[0]))
print(type(channel_arr[0]))
print(type(power_arr[0]))
# n_wavelength = len(wavelength_arr)
# n_channel = len(channel_arr)
# n_power = len(power_arr)
# pp_table = np.random.random((n_power, n_wavelength))
# power_table = np.random.random((n_power, n_wavelength))

# rows = []
# for i, wavelength in enumerate(wavelength_arr):
#     for j, target_power in enumerate(power_arr):
#         rows.append({
#             "Wavelength (nm)": wavelength,
#             "Channel": channel_arr[i],
#             "Target Power (nW)": target_power * 1e+9,
#             "PP (%)": pp_table[i, j],
#             "Measured Power (nW)": power_table[i, j] * 1e+9
#         })

# measured_table = pd.DataFrame(rows)

# print(measured_table)

# measured_power_df = pd.DataFrame(
#     power_table,                 # convert to nW
#     index=wavelength_arr,              # rows
#     columns=power_arr           # columns
# )

# measured_power_df.index.name = "Wavelength (nm)"
# measured_power_df.columns.name = "Target Power (nW)"

# print(measured_power_df)