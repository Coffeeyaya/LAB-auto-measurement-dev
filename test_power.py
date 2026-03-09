from pathlib import Path
import pandas as pd

power_table_path = Path("calibration") / "single_power_multi_wavelength.csv"
if power_table_path.exists():
    power_table = pd.read_csv(power_table_path)
else:
    print("Warning: Power table CSV not found!")
    power_table = None

print(power_table["Wavelength (nm)"].dtype)
print(power_table["Power (nW)"].dtype)
def get_pp_exact(df, wavelength, power_nw):
    row = df[(df["Wavelength (nm)"] == wavelength) &
             (abs(df["Power (nW)"] - power_nw) < 5 * 1e-9)]
    print(row)
    if len(row) == 0:
        return None
    return float(row["PP (%)"].values[0])

print(get_pp_exact(power_table, 532, 100))