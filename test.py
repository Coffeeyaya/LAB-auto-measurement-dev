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