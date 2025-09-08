import time
import os 
from utils.iv_utils import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, change_idvg_vd_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range
from utils.socket_utils import connect_to_server


###-----------------------------------###
CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\data"
os.makedirs(CSV_FOLDER, exist_ok=True)
material = 'mw'
device_number = '7-6'
laser_wavelength = '660nm'
laser_power = '100nw'
rest_time = 60
###-----------------------------------###

# measurement settings
idvg_path = r'D:\kickstart\YunChen\idvg_yunChen\idvg'
idvd_path = r'D:\kickstart\YunChen\idvd_yunChen\idvd'
time_path = r'D:\kickstart\YunChen\timeDependent_yunChen\time'
# save_folder_idvg = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvg'
# save_folder_idvd = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvd'
# save_folder_time = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\time'


# Communication settings
SERVER_IP = "192.168.151.20"   # IP of the laser computer
PORT = 5001
sock = connect_to_server(ip=SERVER_IP, port=PORT)

# start controlling KickStart App
get_window(r'Kick')
scroll_to_bottom()

# --- idvg ---
change_measurement_mode(idvg_path)
# dark idvg
time.sleep(3)
get_window(r'Kick')

if material in ['mw', 'wse2']:
    change_vg_range("5", "-5")
    change_vg_range("5", "-5")
else:
    change_vg_range("-5", "5")
    change_vg_range("-5", "5")

# change_idvg_vd_level("1")
# change_idvg_vd_level("1")

time.sleep(rest_time)
run_measurement()
time.sleep(1)
filename = filename_generator(material, device_number, measurement_type='idvg', condition='dark')
export_data(CSV_FOLDER, filename)

time.sleep(rest_time)

# light idvg
illuminate_and_run(sock)
filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'light_{laser_wavelength}_{laser_power}')
export_data(CSV_FOLDER, filename)

time.sleep(rest_time)

# --- idvd ---
change_measurement_mode(idvd_path)
time.sleep(3)

# change_vd_range("3", "-3")
# change_vd_range("3", "-3")

vg_values = ["-4", "-2", "0", "2", "4"]
for vg in vg_values:
    change_idvd_vg_level(vg)
    change_idvd_vg_level(vg)
    
    # dark idvd
    run_measurement()
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'dark:vg={vg}')
    export_data(CSV_FOLDER, filename)

    time.sleep(rest_time)

    # light idvd
    illuminate_and_run(sock)
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'light_{laser_wavelength}_{laser_power}:vg={vg}')
    export_data(CSV_FOLDER, filename)
    time.sleep(rest_time)

# --- time dependent ---
change_measurement_mode(time_path)
time.sleep(3)
time_dependent_illumination_run(sock)
filename = filename_generator(material, device_number, measurement_type='time', condition='on-off')
export_data(CSV_FOLDER, filename)

print('finish')
