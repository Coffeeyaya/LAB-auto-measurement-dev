from pathlib import Path
import pandas as pd

power_table_path = Path("calibration") / "single_power_multi_wavelength.csv"
if power_table_path.exists():
    power_table = pd.read_csv(power_table_path)
else:
    print("Warning: Power table CSV not found!")
    power_table = None
print(power_table)