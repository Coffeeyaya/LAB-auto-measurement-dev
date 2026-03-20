import numpy as np


def basic_block(channel_idx, vg_on, vg_off, duration_1, duration_2, duration_3, duration_4, on_off_number=1):
    pp = np.random.random()
    
    basic_block = [
        {"Vg": vg_off, "duration": duration_1},
        {"Vg": vg_on, "duration": duration_2, "laser_cmd1": {"channel": channel_idx, "power": pp}}]
    for i in range(on_off_number):
        basic_block.append({"Vg": vg_on, "duration": duration_3, "laser_cmd2": {"channel": channel_idx, "on": 1}}) 
        basic_block.append({"Vg": vg_on, "duration": duration_4, "laser_cmd2": {"channel": channel_idx, "on": 1}})
        
    return basic_block

def print_basic_block(block):
    for b in block:
        print(b)

test_block = basic_block(0, 1, -1, 1, 1, 1, 1, 3)
print_basic_block(test_block)
