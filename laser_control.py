import time
from LabAuto.laser import init_AOTF, grab_and_click_AOTF, change_power_function, press_on_button, change_lambda_function
from LabAuto.network import create_server, Connection

def run_laser_server(host="0.0.0.0", port=5001):
    grid = init_AOTF()
    server_socket = create_server(host, port)
    
    try:
        # OUTER LOOP: Keeps the server alive forever
        while True:
            print("\nWaiting for Electrical Computer to connect...")
            grid = init_AOTF()
            conn, addr = Connection.accept(server_socket)
            print(f"Connected to client at {addr}")
            
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