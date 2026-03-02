import time
import pandas as pd
# Using the functions from your provided files
from LabAuto.laser import init_AOTF, get_coord, change_power_function, move_and_click, change_lambda_function
from LabAuto.network import create_server, Connection

def run_laser_state_machine(host="0.0.0.0", port=5001):
    grid = init_AOTF()
    server_socket = create_server(host, port)
    
    # Define our State Machine Tracking
    current_state = "IDLE" 
    current_vg = None  # To track what the electrical computer is doing
    
    try:
        while True:
            print("Waiting for Electrical Computer to connect...")
            conn, addr = Connection.accept(server_socket)
            
            try:
                while True:
                    # 1. Wait for JSON command from Electrical Computer
                    try:
                        # Expected format: {"cmd": "SET_LIGHT", "state": "ON", "channel": 6, "power": "17"}
                        data = conn.receive_json()
                    except ConnectionError:
                        print("Client disconnected.")
                        break
                    
                    if not data:
                        continue
                        
                    command = data.get("cmd")
                    
                    # ---------------------------------------------------------
                    # STATE MACHINE LOGIC
                    # ---------------------------------------------------------
                    
                    if command == "SET_LIGHT":
                        target_state = data.get("state") # "ON" or "OFF"
                        channel = data.get("channel", 6)
                        power = str(data.get("power", "17"))
                        
                        if target_state == "ON" and current_state != "LIGHT_ON":
                            print(f"State Transition: Turning LIGHT ON (Ch: {channel}, Pwr: {power})")
                            
                            # Execute GUI clicks
                            change_power_function(grid, channel, power)
                            time.sleep(1)
                            on_coord = get_coord(grid, channel, "on")
                            time.sleep(1)
                            move_and_click(on_coord)
                            time.sleep(0.5)
                            
                            current_state = "LIGHT_ON"
                            
                            # Acknowledge back to Electrical Computer
                            conn.send_json({"status": "ACK", "current_state": current_state})
                            
                        elif target_state == "OFF" and current_state != "LIGHT_OFF":
                            print("State Transition: Turning LIGHT OFF")
                            
                            # Execute GUI clicks to turn off
                            on_coord = get_coord(grid, channel, "on")
                            move_and_click(on_coord)
                            time.sleep(0.5)
                            
                            current_state = "LIGHT_OFF"
                            
                            # Acknowledge back to Electrical Computer
                            conn.send_json({"status": "ACK", "current_state": current_state})
                        else:
                            # If already in the correct state, just confirm it
                            conn.send_json({"status": "ACK", "current_state": current_state, "note": "No change needed"})

                    # ---------------------------------------------------------
                    # ELECTRICAL COMPUTER UPDATING LIGHT COMPUTER
                    # ---------------------------------------------------------
                    elif command == "UPDATE_VG":
                        current_vg = data.get("vg")
                        print(f"Sync: Electrical Computer reports Vg is now {current_vg}V")
                        # Light computer can log this state or just acknowledge
                        conn.send_json({"status": "ACK", "msg": "Vg state recorded"})

                    elif command == "GET_STATUS":
                        # Allow Electrical Computer to poll current status
                        conn.send_json({
                            "status": "OK", 
                            "light_state": current_state,
                            "known_vg": current_vg
                        })
                        
                    else:
                        conn.send_json({"status": "ERROR", "msg": "Unknown command"})

            finally:
                conn.close()
                print("Connection closed. Returning to IDLE state.")
                current_state = "IDLE"
                current_vg = None
                
    finally:
        server_socket.close()

if __name__ == "__main__":
    run_laser_state_machine()