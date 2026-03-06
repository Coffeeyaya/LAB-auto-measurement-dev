import numpy as np
sequence = []
idx_arr = np.arange(0, 4, 1).astype(str) # ['0' '1' '2' '3']
def get_basic_block(idx):
    basic_block = [
        {"Vg": -1.5, "duration": 3},
        {"Vg": 0.5, "duration": 10, 
        "laser_cmd1": {"channel": idx, "wavelength": 532}}, 
        {"Vg": 0.5, "duration": 5, 
        "laser_cmd2": {"channel": idx, "on": 1}}, 
        {"Vg": 0.5, "duration": 5, 
        "laser_cmd2": {"channel": idx, "on": 1}}, 
    ]
    return basic_block
for i in range(len(idx_arr)):
    idx = idx_arr[i]
    sequence.extend(get_basic_block(idx))
print(idx_arr)
print(sequence)