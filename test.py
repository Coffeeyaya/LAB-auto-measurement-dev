import numpy as np
import pandas as pd
import json
from pathlib import Path

pp_table = np.random.random((2,2))
wavelength_arr = [450, 532]
power_arr = [100, 200]

pp_df = pd.DataFrame(
        pp_table,                 
        index=wavelength_arr,       # rows
        columns=power_arr           # columns
        )

pp_df.to_csv('pp_df.csv', index=True)
# measured_power_df.to_csv('measured_power_df.csv', index=True)
