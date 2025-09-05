import time
import os 
from utils.iv_utils import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range
from utils.socket_utils import connect_to_server

# measurement settings
idvg_path = r'D:\kickstart\YunChen\idvg_yunChen\idvg'
idvd_path = r'D:\kickstart\YunChen\idvd_yunChen\idvd'
time_path = r'D:\kickstart\YunChen\timeDependent_yunChen\time'
# save_folder_idvg = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvg'
# save_folder_idvd = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvd'
# save_folder_time = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\time'
CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\data"
os.makedirs(CSV_FOLDER, exist_ok=True)
material = 'mw'
device_number = '5-5'
laser_wavelength = '660nm'
laser_power = '100nw'

# Communication settings
# SERVER_IP = "192.168.151.20"   # IP of the laser computer
# PORT = 5001
# sock = connect_to_server(ip=SERVER_IP, port=PORT)

# start controlling KickStart App
get_window(r'Kick')
# scroll_to_bottom()

# --- idvg ---
change_measurement_mode(idvg_path)
# dark
time.sleep(3)
for i in range(1, 3):
    if material in ['mw', 'wse2']:
        change_vg_range(str(i), '-' + str(i))
    else:
        change_vg_range('-' + str(i), str(i))
    time.sleep(1)
    run_measurement()
    time.sleep(1)

# run_measurement()

# filename = filename_generator(material, device_number, measurement_type='idvg', condition='dark')
# export_data(CSV_FOLDER, filename)

# time.sleep(5)
# # light
# illuminate_and_run(sock)
# filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'light_{laser_wavelength}_{laser_power}')
# export_data(CSV_FOLDER, filename)
# time.sleep(5)

# # --- idvd ---
# change_measurement_mode(idvd_path)
# time.sleep(3)
for i in range(1, 3):
    if material in ['mw', 'wse2']:
        change_vd_range('-' + str(i), str(i))
    else:
        change_vd_range('-' + str(i), str(i))
    time.sleep(1)
    run_measurement()
    time.sleep(1)
# change_vd_range("3", "-3")

# vg_values = ["-5", "0", "5"]
# scroll_to_bottom()
# for vg in vg_values:
#     change_idvd_vg_level(vg)
#     # dark
#     run_measurement()
#     filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'dark:vg={vg}')
#     export_data(CSV_FOLDER, filename)

#     time.sleep(5)
#     # light
#     illuminate_and_run(sock)
#     filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'light_{laser_wavelength}_{laser_power}:vg={vg}')
#     export_data(CSV_FOLDER, filename)
#     time.sleep(5)

# # --- time dependent ---
# # laser off
# change_measurement_mode(time_path)

# time_dependent_illumination_run(sock)
# filename = filename_generator(material, device_number, measurement_type='time', condition='on-off')
# export_data(CSV_FOLDER, filename)

# print('finish')
