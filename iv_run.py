import time
from iv_utils import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, stop_measurement, export_data, change_idvd_vg_level
import socket
from socket_utils import send_cmd, wait_for

# measurement settings
idvg_path = r'D:\kickstart\YunChen\idvg_yunChen\idvg'
idvd_path = r'D:\kickstart\YunChen\idvd_yunChen\idvd'
time_path = r'D:\kickstart\YunChen\timeDependent_yunChen\time'
save_folder_idvg = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvg'
save_folder_idvd = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\idvd'
save_folder_time = r'C:\Users\mmm11\OneDrive\桌面\yun-chen\KickStart\hs2\20250901\time'

material = 'mw'
device_number = '5-5'
laser_wavelength = '660nm'
laser_power = '100nw'

# Communication settings
SERVER_IP = "192.168.151.20"   # IP of the laser computer
PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, PORT))

def filename_generator(material, device_number, measurement_type, condition):
    return f'{material}_{measurement_type}_{device_number}_{condition}'

def illuminate_and_run():
    send_cmd(sock, "ON")
    wait_for(sock, "ON")
    time.sleep(30) # ex: wait 30 s
    run_measurement()

    send_cmd(sock, "OFF")
    wait_for(sock, "OFF")

def time_dependent_illumination_run():
    run_measurement()
    send_cmd(sock, "FUNCTION")
    time.sleep(30)
    wait_for(sock, "FUNCTION_DONE")
    time.sleep(30)
    stop_measurement()

# start controlling KickStart App
get_window(r'Kick')
scroll_to_bottom()

# --- idvg ---
change_measurement_mode(idvg_path)

run_measurement()
filename = filename_generator(material, device_number, measurement_type='idvg', condition='dark')
export_data(save_folder_idvg, filename)
time.sleep(60)
illuminate_and_run()
filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'light_{laser_wavelength}_{laser_power}')
export_data(save_folder_idvg, filename)


# --- idvd ---
change_measurement_mode(idvd_path)
vg_values = ["-5", "-2", "0", "2", "5"]
for vg in vg_values:
    scroll_to_bottom()
    change_idvd_vg_level(vg)

    run_measurement()
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'dark:vg={vg}')
    export_data(save_folder_idvd, filename)
    time.sleep(60)
    illuminate_and_run()
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'light_{laser_wavelength}_{laser_power}:vg={vg}')
    export_data(save_folder_idvd, filename)
    time.sleep(60)

# --- time dependent ---
# laser off
change_measurement_mode(time_path)

time_dependent_illumination_run()
filename = filename_generator(material, device_number, measurement_type='time', condition='on-off')
export_data(save_folder_time, filename)

print('finish')
