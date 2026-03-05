import time
import os 
from pathlib import Path
from LabAuto.iv import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, change_idvg_vd_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range, time_dependent_dark_current, time_dependent_illumination_run_no_wait, time_dependent_function_run
from LabAuto.network import create_server, Connection

# params
material = 'mos2'
device_number = '1-1'
measurement_index = '0'
laser_function = 'wavelength'
rest_time = 1
dark_time1 = 1
dark_time2 = 1

# data saving folder
CSV_FOLDER = Path(__file__).parent.parent / 'send_data'
os.makedirs(CSV_FOLDER, exist_ok=True)
 
# kickstart measurement path
idvg_path = r'D:\kickstart\YunChen\IDVG\IDVG'
idvd_path = r'D:\kickstart\YunChen\IDVD\IDVD'
time_path = r'D:\kickstart\YunChen\TIME\TIME'

# act as client, connect to win 7 server
WIN_7_SERVER_IP = "192.168.50.17"
WIN_7_PORT = 5001


def TIME(laser_conn, material, device_number, measurement_index, laser_function, rest_time=60, dark_time1=60, dark_time2=60):
    '''
    rest_time: time rested before measurement
    wait_time: start measurement ~ start illumination, stop illumination ~ end measurement
    '''
    rest_time = int(rest_time)
    reset_mode = True
    get_window(r'Kick')
    if get_window(r'KickStart - TIME'):
        reset_mode = False
    if reset_mode:
        change_measurement_mode(time_path)
        time.sleep(3)

    time.sleep(rest_time)

    time_dependent_function_run(laser_conn, laser_function=laser_function , dark_time1=dark_time1, dark_time2=dark_time2)
    time.sleep(1)
    filename = filename_generator(material, device_number, measurement_type='time', condition=f'onoff-{measurement_index}')
    export_data(CSV_FOLDER, filename)

def set_vg(vg_value):
    change_idvd_vg_level(vg_value)
    change_idvd_vg_level(vg_value)

def main():
    # act as client, connect to laser computer (win 7)
    laser_conn = Connection.connect(WIN_7_SERVER_IP, WIN_7_PORT)

    # after all computers are connected, start controlling kickstart
    get_window(r'Kick')
    scroll_to_bottom()

    time.sleep(2)
    TIME(laser_conn, material, device_number, measurement_index, laser_function=laser_function, rest_time=rest_time, dark_time1=dark_time1, dark_time2=dark_time2)    

if __name__ == '__main__':
    main()
    
    
