import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def exp_func_shift(x, a, b, c):
    return a * np.exp(-b * (x - x_axis[0])) + c

wavelength_power_arr = [["450", "115"], ["488", "77"], ["514", "34.4"], ["532", "33"],
                        ["600", "25.5"], ["633", "20.2"], ["660", "17"], ["680", "17"]]
wavelength_power_arr = np.array(wavelength_power_arr, dtype=float)
x_axis = wavelength_power_arr[:, 0]
y_axis = wavelength_power_arr[:, 1]

params, _ = curve_fit(exp_func_shift, x_axis, y_axis, p0=(1, -0.01, 1))
x_new = np.linspace(450, 680, 15)
y_new = exp_func_shift(x_new, *params)

plt.scatter(x_axis, y_axis, color='red', label='Original data')
plt.scatter(x_new, y_new, color='blue', label='exp ift')
plt.xlabel('Wavelength (nm)')
plt.ylabel('Power')
plt.legend()
plt.show()

power_arr = np.zeros_like(x_new)
df = pd.DataFrame({
    'wavelength_arr': x_new,
    'power_percentage_arr': y_new,
    'power_arr': power_arr
})
df.to_csv('wavelength_power.csv', index=None, header=df.columns)
