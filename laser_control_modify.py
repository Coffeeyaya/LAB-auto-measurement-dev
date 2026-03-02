import time
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click
# from LabAuto.laser_bg import init_AOTF, get_coord, change_power_function, background_click, background_double_click, background_paste
from LabAuto.network import create_server, Connection

import win32gui
import win32con
import win32api

def run_laser_server(host="0.0.0.0", port=5001):
    grid = init_AOTF()
    hwnd = win32gui.FindWindow(None, "AOTF Controller")
    server_socket = create_server(host, port)
    
    current_state = "OFF"
    
    try:
        while True:
            print("Waiting for Electrical Computer to connect...")
            grid = init_AOTF()
            conn, addr = Connection.accept(server_socket)
            
            try:
                while True:
                    try:
                        # Wait for command: {"cmd": "SET_LIGHT", "state": "ON", "channel": 6, "power": "17"}
                        data = conn.receive_json()
                    except ConnectionError:
                        print("Electrical computer disconnected.")
                        break
                    
                    if not data:
                        continue
                        
                    command = data.get("cmd")
                    
                    if command == "SET_LIGHT":
                        target_state = data.get("state")
                        channel = data.get("channel", 6)
                        power = str(data.get("power", "17"))
                        
                        if target_state == "ON" and current_state != "ON":
                            print(f"Turning LIGHT ON (Ch: {channel}, Pwr: {power})")
                            # change_power_function(hwnd, grid, channel, power)
                            change_power_function(grid, channel, power)
                            time.sleep(1)
                            
                            on_coord = get_coord(grid, channel, "on")
                            # background_click(hwnd, on_coord[0], on_coord[1])
                            time.sleep(1)
                            move_and_click(on_coord)
                            time.sleep(0.5)

                            
                            current_state = "ON"
                            
                        elif target_state == "OFF" and current_state != "OFF":
                            print("Turning LIGHT OFF")
                            on_coord = get_coord(grid, channel, "on")
                            # background_click(hwnd, on_coord[0], on_coord[1])
                            move_and_click(on_coord)
                            time.sleep(0.5)
                            
                            current_state = "OFF"
                        
                        # Tell the Electrical Computer we are finished clicking
                        conn.send_json({"status": "ACK", "state": current_state})

            finally:
                conn.close()
                print("Connection closed. Laser staying in last known state.")
                
    finally:
        server_socket.close()

if __name__ == "__main__":
    run_laser_server()