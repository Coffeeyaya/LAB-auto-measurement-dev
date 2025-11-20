import pandas as pd
import numpy as np

wavelength_arr = np.linspace(400, 700, 31, dtype=int)
power_percentage_arr = np.zeros_like(wavelength_arr)
power_arr = np.zeros_like(wavelength_arr)

df = pd.DataFrame({
    'wavelength_arr': wavelength_arr,
    'power_percentage_arr': power_percentage_arr,
    'power_arr': power_arr
})

df.to_csv('test.csv', index=None, header=df.columns)