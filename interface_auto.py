import os
import time
from LabAuto.network import Connection  # same Connection used by iv_run
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

WIN_7_SERVER_IP = "192.168.50.17"
WIN_7_PORT = 5000
# WIN_7_PORT = 5001
WIN_10_SERVER_IP = "192.168.50.101"
# WIN_10_PORT = 5000 # if on mac
WIN_10_PORT = 7000 # if on win10
WIN_10_PORT_IV_RUN = 6000

def celebrate_animation():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor('black')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    n = 500
    x = np.random.rand(n)
    y = np.random.rand(n)
    colors = np.random.rand(n, 3)
    sizes = np.random.randint(20, 80, n)
    scat = ax.scatter(x, y, s=sizes, c=colors)

    def update(frame):
        scat.set_offsets(np.c_[np.random.rand(n), np.random.rand(n)])
        return scat,

    ani = FuncAnimation(fig, update, frames=30, interval=150, blit=True, repeat=False)

    plt.show(block=False)
    plt.pause(5)  # <-- let it run for 5 seconds before window closes
    plt.close()

def listen_to_server(win_10_iv_conn):
    """
    listened to server for progress updates
    """
    msg = win_10_iv_conn.receive_json()
    if not msg:
        return False
    cmd = msg.get("cmd", "")
    if cmd == "PROGRESS":
        if msg.get('progress') == 'finished':
            # celebrate_animation()
            return True
        else:
            print(msg.get('progress'))
            return False
    return False
    
def send_params(win_10_iv_conn, params):
    time.sleep(1)
    win_10_iv_conn.send_json(params)

def change_params(params, key_values_pairs):
    params_copy = params.copy()
    for k, v in key_values_pairs.items():
        params_copy[k] = v
    return params_copy

params = {
        "material": "mos2",
        "device_number": "3-6",
        "measurement_type": "time",
        "measurement_index": "0",
        "laser_function": "wavelength",
        "vg_value": "None",
        "rest_time": "1",
        "dark_time1": "1",
        "dark_time2": "1",
    }

# work_flow = [
#     {'measurement_index': '0'},
#     # {'measurement_type': 'time', 'laser_function': 'wavelength'}
# ]

# steady state
# work_flow = [
#     {"measurement_index": "0", "vg_value": "-2"},
#     {"measurement_index": "1", "vg_value": "0"},
#     {"measurement_index": "2", "vg_value": "2"}
# ]

def get_vg_value(wavelength, set_vg_value):
    if int(wavelength) == 450:
        return set_vg_value
    else:
        return "None"

# transient
wavelength_arr = np.linspace(450, 680, 24, dtype=int).astype(str)

work_flow_vg1 = [
    {
        "measurement_index": f"{i}",
        "laser_function": f"wavelength,{wavelength_arr[i]}",
        "vg_value": get_vg_value(wavelength_arr[i], "-2")
    }
    for i in range(len(wavelength_arr))
]

work_flow_vg2 = [
    {
        "measurement_index": f"{i}",
        "laser_function": f"wavelength,{wavelength_arr[i]}",
        "vg_value": get_vg_value(wavelength_arr[i], "0")
    }
    for i in range(len(wavelength_arr))
]

work_flow_vg3 = [
    {
        "measurement_index": f"{i}",
        "laser_function": f"wavelength,{wavelength_arr[i]}",
        "vg_value": get_vg_value(wavelength_arr[i], "2")
    }
    for i in range(len(wavelength_arr))
]

work_flow = work_flow_vg1 + work_flow_vg2 + work_flow_vg3


if __name__ == "__main__":
    try:
        win_7_conn = Connection.connect(WIN_7_SERVER_IP, WIN_7_PORT)
        win_10_conn = Connection.connect(WIN_10_SERVER_IP, WIN_10_PORT)
        
        num_of_params = len(work_flow)
        current_idx = 0
        expected_idx = 0
        
        while (current_idx < num_of_params):
            if expected_idx == current_idx:
                expected_idx += 1 # for sending params of next measurement
                win_7_conn.send_json({"cmd": "RUN", "target": "laser_control.py"})
                win_10_conn.send_json({"cmd": "RUN", "target": "iv_run.py"})
                time.sleep(1)
                win_10_iv_conn = Connection.connect(WIN_10_SERVER_IP, WIN_10_PORT_IV_RUN)
                time.sleep(1)
                current_params = change_params(params, work_flow[current_idx])
                send_params(win_10_iv_conn, current_params)

            if listen_to_server(win_10_iv_conn):
                current_idx += 1 # only increment when finish current measurement
                win_7_conn.send_json({"cmd": "KILL", "target": "laser_control.py"})
                win_10_conn.send_json({"cmd": "KILL", "target": "iv_run.py"})
        
    finally:
        celebrate_animation()
        win_7_conn.send_json({"cmd": "KILL", "target": "laser_control.py"})
        win_10_conn.send_json({"cmd": "KILL", "target": "iv_run.py"})


