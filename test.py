import pandas as pd
import numpy as np
import os 
from pathlib import Path

def get_pp_exact(df, wavelength, power_nw):
    if df is None: return None
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        print(f"Warning: Cannot convert {power_nw}nW to PP for {wavelength}nm.")
        return None
    
folder = '/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/measure/calibration'
pp_path = Path(folder) / 'pp_df.csv'
df = pd.read_csv(pp_path, index_col=0)
print(df)
pp = get_pp_exact(df, "660", "100")
print(pp)


# def get_pp_exact(df, wavelength, power_nw):
#     if df is None: return None
#     try:
#         return float(df.loc[int(wavelength), str(power_nw)])
#     except KeyError:
#         print(f"Warning: Cannot convert {power_nw}nW to PP for {wavelength}nm.")
#         return None

# col_l1, col_l2, col_l3, col_l4 = st.columns(4)
# col_l1.number_input("Channel", step=1, key="idvg_laser_channel", disabled=is_disabled)
# col_l2.number_input("Wavelength (nm)", step=1, key="idvg_laser_wavelength", disabled=is_disabled)
# col_l3.number_input("Power (nW)", step=1.0, key="idvg_laser_power", disabled=is_disabled)
# col_l4.number_input("Laser Stable Time (s)", step=1, key="idvg_laser_stable_time", disabled=is_disabled)
