import time
import os 
from pathlib import Path
from LabAuto.iv import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, change_idvg_vd_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run, change_vg_range, change_vd_range, time_dependent_dark_current, time_dependent_illumination_run_no_wait, time_dependent_function_run
from LabAuto.network import create_server, Connection

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
# act as server, accept mac client
WIN_10_PORT = 6000

def set_vg(vg_value):
    change_idvd_vg_level(vg_value)
    change_idvd_vg_level(vg_value)
    
def IDVG(mac_conn, laser_conn, material, device_number, measurement_index, rest_time=60):
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

def IDVD(mac_conn, laser_conn, material, device_number, measurement_index, vg_values, rest_time=60):
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

def TIME(mac_conn, laser_conn, material, device_number, measurement_index, laser_function, vg_value=None, rest_time=60, dark_time1=60, dark_time2=60):
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
    
    if vg_value:
        set_vg(vg_value)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": f"wait {rest_time} s"})
    time.sleep(rest_time)

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "time measurement started"})
    time_dependent_function_run(laser_conn, laser_function=laser_function , dark_time1=dark_time1, dark_time2=dark_time2)
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
    # act as client, connect to laser computer (win 7)
    laser_conn = Connection.connect(WIN_7_SERVER_IP, WIN_7_PORT)

    # act as server, accept client_iv (mac)
    server_socket = create_server("0.0.0.0", WIN_10_PORT)
    mac_conn, addr = Connection.accept(server_socket)

    # after all computers are connected, start controlling kickstart
    get_window(r'Kick')
    scroll_to_bottom()

    print("[IV_RUN] Waiting for connection from Interface...")
    params = mac_conn.receive_json()  # Just wait for parameters
    print("[IV_RUN] Received parameters:", params)

    material = params.get("material", "mos2_default")
    device_number = params.get("device_number", "0-0_default")
    measurement_type = params.get("measurement_type", "idvg")
    measurement_index = params.get("measurement_index", "0")
    laser_function = params.get("laser_function", "1_on_off")
    try:
        vg_value = params.get("vg_value", "0")
        if vg_value == "None":
            vg_value = None
    except:
        vg_value = "0"

    try:
        rest_time = int(params.get("rest_time", "60"))
    except:
        rest_time = 5
    try:
        dark_time1 = int(params.get("dark_time1", "60"))
    except:
        dark_time1 = 5
    try:
        dark_time2 = int(params.get("dark_time2", "60"))
    except:
        dark_time2 = 5

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "Measurement started"})
    time.sleep(2)

    if measurement_type == 'idvg':
        IDVG(mac_conn, laser_conn, material, device_number, measurement_index, rest_time=rest_time)
    elif measurement_type == 'idvd':
        IDVD(mac_conn, laser_conn, material, device_number, measurement_index, vg_values=['3', '4', '5'], rest_time=rest_time)
    elif measurement_type == 'time':
        TIME(mac_conn, laser_conn, material, device_number, measurement_index, laser_function=laser_function, vg_value=vg_value,
              rest_time=rest_time, dark_time1=dark_time1, dark_time2=dark_time2)

    else:
        mac_conn.send_json({"cmd": "PROGRESS", "progress": "invalid measurement type"})

    mac_conn.send_json({"cmd": "PROGRESS", "progress": "finished"})
    print("[IV_RUN] Finished all measurements.")
    mac_conn.send_json({"cmd": "PROGRESS", "progress": "finished"})

if __name__ == '__main__':
    main()
    
    
