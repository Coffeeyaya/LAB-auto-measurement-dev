import time
import os 
from utils.iv_utils import get_window, scroll_to_bottom, change_measurement_mode, \
    run_measurement, export_data, change_idvd_vg_level, filename_generator, \
    illuminate_and_run, time_dependent_illumination_run
from utils.socket_utils import connect_to_server

SERVER_IP = "192.168.151.20"   # IP of the laser computer
PORT = 5001
sock = connect_to_server(ip=SERVER_IP, port=PORT)