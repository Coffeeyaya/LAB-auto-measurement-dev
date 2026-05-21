import time
import io
import base64
import pyautogui
import pygetwindow as gw
from LabAuto.laser import init_AOTF, grab_and_click_AOTF, change_power_function, press_on_button, change_lambda_function
from LabAuto.network import create_server, Connection

def take_snapshot():
    """Takes a screenshot of the AOTF Controller window and returns it as a base64 string."""
    try:
        win_list = gw.getWindowsWithTitle("AOTF Controller")
        if not win_list:
            return None
        win = win_list[0]
        # Ensure window is visible
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.1) # Wait for focus
        
        screenshot = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"Snapshot error: {e}")
        return None

def run_laser_server(host="0.0.0.0", port=5001):
    server_socket = create_server(host, port)
    
    try:
        # OUTER LOOP: Keeps the server alive forever
        while True:
            print("\nWaiting for Electrical Computer to connect...")
            conn, addr = Connection.accept(server_socket)
            print(f"Connected to client at {addr}")
            
            # Refocus and get grid mapping ONLY after connection is established
            grid = init_AOTF() 
            
            try:
                # INNER LOOP: Handles the active connection
                while True:
                    try:
                        data = conn.receive_json()
                    except Exception as e:
                        print(f"Electrical computer disconnected (Receive Error): {e}")
                        break # Break inner loop, go back to waiting for new connection
                    
                    if not data:
                        continue
                    
                    command = data.get("command")
                    if command == "snapshot":
                        print("Snapshot requested!")
                        img_base64 = take_snapshot()
                        if img_base64:
                            conn.send_json({"response": "SUCCESS", "image": img_base64})
                        else:
                            conn.send_json({"response": "ERROR", "message": "Could not take snapshot"})
                        continue

                    ###    
                    print("Command received! Refocusing AOTF Window...")
                    grab_and_click_AOTF()
                    ###

                    channel_recv = data.get("channel")
                    wavelength_recv = data.get("wavelength")
                    power_recv = data.get("power")
                    on_recv = data.get("on")
                    
                    try:
                        # FIXED BUG: Used 'is not None' because Channel 0 evaluates to False in standard 'if' statements!
                        if channel_recv is not None and wavelength_recv is not None: 
                            change_lambda_function(grid, int(channel_recv), str(wavelength_recv))
                            time.sleep(1)
                            
                        if channel_recv is not None and power_recv is not None:
                            change_power_function(grid, int(channel_recv), str(power_recv))
                            time.sleep(1)
                            
                        if channel_recv is not None and on_recv is not None:
                            press_on_button(grid, int(channel_recv))
                            
                        # Tell the Electrical Computer we are finished clicking
                        conn.send_json({"response": "ACK"})
                        
                    except Exception as e:
                        print(f"Error during GUI automation or sending ACK: {e}")
                        break # Drop this broken connection, go back to waiting

            finally:
                conn.close()
                print("Connection closed. Laser staying in last known state.")
                
    finally:
        server_socket.close()

if __name__ == "__main__":
    run_laser_server()