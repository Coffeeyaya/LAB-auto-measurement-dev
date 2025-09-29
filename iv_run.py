import time
import os 
from LabAuto.iv import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, change_idvg_vd_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range, time_dependent_dark_current
from LabAuto.network import create_server, Connection

###-----------------------------------###
CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\LAB-auto-measurement-dev\send_data"
os.makedirs(CSV_FOLDER, exist_ok=True)

###-----------------------------------###
laser_wavelength = '660nm'
laser_power = '100nw'
rest_time = 60
###-----------------------------------###

# measurement settings
idvg_path = r'D:\kickstart\YunChen\IDVG\IDVG'
idvd_path = r'D:\kickstart\YunChen\IDVD\IDVD'
time_path = r'D:\kickstart\YunChen\TIME\TIME'

# connect to laser computer (win 7)
SERVER_IP = "192.168.151.20"
PORT = 5001
laser_conn = Connection.connect(SERVER_IP, PORT)

# accept client_iv (mac)
server_socket = create_server("0.0.0.0", 6000)
mac_conn, addr = Connection.accept(server_socket)


# start controlling KickStart App
get_window(r'Kick')
scroll_to_bottom()

mac_conn.send_json({"cmd": "REQUEST_PARAMS", "message": "Please enter parameters"})
params = mac_conn.receive_json()
print("Received parameters from Mac:", params)

material = params.get("material", "default")
device_number = params.get("device_number", "default")

mac_conn.send_json({"cmd": "PROGRESS", "progress": "Measurement started"})
time.sleep(2)
mac_conn.send_json({"cmd": "PROGRESS", "progress": "idvg"})


# --- idvg ---
# change_measurement_mode(idvg_path)
# # dark idvg
# time.sleep(3)
# get_window(r'Kick')
# vg_1 = "5"
# vg_2 = "-5"
# if material in ['mw', 'wse2']:
#     change_vg_range(vg_1, vg_2)
#     change_vg_range(vg_1, vg_2)
#     vg_start = vg_1
#     vg_end = vg_2
# else:
#     change_vg_range(vg_2, vg_1)
#     change_vg_range(vg_2, vg_1)
#     vg_start = vg_2
#     vg_end = vg_1

# # change_idvg_vd_level("1")
# # change_idvg_vd_level("1")

# for i in range(2):
#     run_measurement()
#     time.sleep(1)
#     filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'dark-{i}')
#     export_data(CSV_FOLDER, filename)
#     time.sleep(rest_time)

# time.sleep(rest_time)

# # light idvg
# for i in range(2):
#     illuminate_and_run(sock)
#     filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'light-{i}')
#     export_data(CSV_FOLDER, filename)

#     time.sleep(rest_time)


'''
time.sleep(2)
mac_conn.send_json({"cmd": "PROGRESS", "progress": "idvd"})

# --- idvd ---
change_measurement_mode(idvd_path)
time.sleep(3)

# change_vd_range("0", "1.5")
# change_vd_range("0", "1.5")


vg_values = ["-3"]
for vg in vg_values:
    change_idvd_vg_level(vg)
    change_idvd_vg_level(vg)
    
    # dark idvd
    run_measurement()
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'dark-vg={vg}')
    export_data(CSV_FOLDER, filename)

    time.sleep(rest_time)

    # light idvd
    illuminate_and_run(sock)
    filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'light-{laser_wavelength}-{laser_power}-vg={vg}')
    export_data(CSV_FOLDER, filename)
    time.sleep(rest_time)
'''

# --- time dependent ---
time.sleep(2)
mac_conn.send_json({"cmd": "PROGRESS", "progress": "time"})
change_measurement_mode(time_path)
time.sleep(3)
time_dependent_illumination_run(laser_conn, wait_time=5)
time.sleep(1)
filename = filename_generator(material, device_number, measurement_type='time', condition=f'onoff')
export_data(CSV_FOLDER, filename)

time.sleep(30)

time_dependent_dark_current()
time.sleep(1)
filename = filename_generator(material, device_number, measurement_type='time', condition=f'onoff-darkcurrent')
export_data(CSV_FOLDER, filename)

print('finish')
