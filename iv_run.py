import time
import os 
from pathlib import Path
from LabAuto.iv import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, change_idvg_vd_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range, time_dependent_dark_current, time_dependent_illumination_run_no_wait
from LabAuto.network import create_server, Connection


###-----------------------------------###
# CSV_FOLDER = r"C:\Users\mmm11\OneDrive\桌面\yun-chen\code\auto\send_data"
CSV_FOLDER = Path(__file__).parent.parent / 'send_data'
os.makedirs(CSV_FOLDER, exist_ok=True)
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

def IDVG(material, device_number, measurement_index, rest_time=60):
    reset_mode = True
    get_window(r'Kick')
    if get_window(r'KickStart - IDVG'):
        reset_mode = False
    if reset_mode:
        mac_conn.send_json({"cmd": "PROGRESS", "progress": "change mode: idvg"})
        change_measurement_mode(idvg_path)
        time.sleep(3)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "set parameters"})
    vg_1 = "5"
    vg_2 = "-5"
    if material in ['mw', 'wse2']:
        change_vg_range(vg_1, vg_2)
        change_vg_range(vg_1, vg_2)
    else:
        change_vg_range(vg_2, vg_1)
        change_vg_range(vg_2, vg_1)    
    # change_idvg_vd_level("1")
    # change_idvg_vd_level("1")


    mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time}"})
    time.sleep(rest_time)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "measure idvg dark"})
    for i in range(1):
        run_measurement()
        time.sleep(1)
        filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'dark-{measurement_index}')
        export_data(CSV_FOLDER, filename)
        # time.sleep(rest_time)
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "idvg dark finished"})

    mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time}"})
    time.sleep(rest_time)
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "measure idvg light"})
    for i in range(1):
        illuminate_and_run(laser_conn)
        filename = filename_generator(material, device_number, measurement_type='idvg', condition=f'light-{measurement_index}')
        export_data(CSV_FOLDER, filename)
        # time.sleep(rest_time)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "idvg light finished"})

def IDVD(material, device_number, measurement_index, vg_values, rest_time=60):
    reset_mode = True
    get_window(r'Kick')
    if get_window(r'KickStart - IDVD'):
        reset_mode = False
    if reset_mode:
        mac_conn.send_json({"cmd": "PROGRESS", "progress": "change mode: idvd"})
        change_measurement_mode(idvd_path)
        time.sleep(3)

    # change_vd_range("0", "1.5")
    # change_vd_range("0", "1.5")

    for vg in vg_values:
        change_idvd_vg_level(vg)
        change_idvd_vg_level(vg)
        
        # dark idvd
        mac_conn.send_json({"cmd": "PROGRESS", "progress": f"measure idvd dark, vg = {vg}"})
        run_measurement()
        filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'dark-vg={vg}-{measurement_index}')
        export_data(CSV_FOLDER, filename)
        mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time}"})
        time.sleep(rest_time)

        # light idvd
        mac_conn.send_json({"cmd": "PROGRESS", "progress": f"measure idvd light, vg = {vg}"})
        illuminate_and_run(laser_conn)
        filename = filename_generator(material, device_number, measurement_type='idvd', condition=f'light-vg={vg}-{measurement_index}')
        export_data(CSV_FOLDER, filename)
        mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time}"})
        time.sleep(rest_time)
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "idvd finished"})

def TIME(material, device_number, measurement_index, rest_time=60, wait_time=60):
    '''
    rest_time: time rested before measurement
    wait_time: start measurement ~ start illumination, stop illumination ~ end measurement
    '''
    reset_mode = True
    get_window(r'Kick')
    if get_window(r'KickStart - TIME'):
        reset_mode = False
    if reset_mode:
        mac_conn.send_json({"cmd": "PROGRESS", "progress": "change mode: time"})
        change_measurement_mode(time_path)
        time.sleep(3)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time} s"})
    time.sleep(rest_time)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "time measurement started"})
    time_dependent_illumination_run(laser_conn, wait_time=wait_time)
    time.sleep(1)
    filename = filename_generator(material, device_number, measurement_type='time', condition=f'onoff-{measurement_index}')
    export_data(CSV_FOLDER, filename)
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "time measurement finished"})

    # time.sleep(10)
    # mac_conn.send_json({"cmd": "PROGRESS", "progress": "darkcurrent measurement started"})
    # time_dependent_dark_current(wait_time=wait_time)
    # time.sleep(1)
    # filename = filename_generator(material, device_number, measurement_type='time', condition=f'onoff-darkcurrent-{measurement_index}')
    # export_data(CSV_FOLDER, filename)
    # mac_conn.send_json({"cmd": "PROGRESS", "progress": "darkcurrent measurement finished"})


def main():
    get_window(r'Kick')
    scroll_to_bottom()

    print("[IV_RUN] Waiting for connection from Interface...")
    params = mac_conn.receive_json()  # Just wait for parameters
    print("[IV_RUN] Received parameters:", params)

    material = params.get("material", "default")
    device_number = params.get("device_number", "default")
    measurement_type = params.get("measurement_type", "default_type")
    measurement_index = params.get("measurement_index", "0")

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "Measurement started"})
    time.sleep(2)

    if measurement_type == 'idvg':
        IDVG(material, device_number, measurement_index)
    elif measurement_type == 'idvd':
        IDVD(material, device_number, measurement_index, vg_values=['3', '4', '5'])
    elif measurement_type == 'time':
        TIME(material, device_number, measurement_index)
    else:
        mac_conn.send_json({"cmd": "PROGRESS", "progress": "invalid measurement type"})

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "finished"})
    print("[IV_RUN] Finished all measurements.")


if __name__ == '__main__':
    main()
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "finished"})
    
