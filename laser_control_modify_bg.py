import time
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click
# from LabAuto.laser_bg import init_AOTF, get_coord, change_power_function, background_click, background_double_click, background_paste, press_on_button, change_lambda_function
from LabAuto.network import create_server, Connection

import win32gui
import win32con
import win32api

def run_laser_server(host="0.0.0.0", port=5001):
    grid = init_AOTF()
    hwnd = win32gui.FindWindow(None, "AOTF Controller")
    server_socket = create_server(host, port)
    
    try:
        while True:
            print("Waiting for Electrical Computer to connect...")
            grid = init_AOTF()
            conn, addr = Connection.accept(server_socket)
            
            try:
                while True:
                    try:
                        data = conn.receive_json()
                    except ConnectionError:
                        print("Electrical computer disconnected.")
                        break
                    
                    if not data:
                        continue
                        
                    channel_recv = data.get("channel", None)
                    wavelength_recv = data.get("wavelength", None)
                    power_recv = data.get("power", None)
                    on_recv = data.get("on", None)

                    if channel_recv and wavelength_recv: 
                        change_lambda_function(hwnd, grid, channel_recv, str(wavelength_recv))
                        time.sleep(1)
                    if channel_recv and power_recv:
                        change_power_function(hwnd, grid, channel_recv, str(power_recv))
                        time.sleep(1)
                    if channel_recv and on_recv:
                        press_on_button(hwnd, grid, channel_recv)
                        # Tell the Electrical Computer we are finished clicking
                    conn.send_json({"response": "ACK"})

            finally:
                conn.close()
                print("Connection closed. Laser staying in last known state.")
                
    finally:
        server_socket.close()

if __name__ == "__main__":
    run_laser_server()