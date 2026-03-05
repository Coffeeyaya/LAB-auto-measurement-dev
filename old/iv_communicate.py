import time
from LabAuto.network import Connection # Assuming network.py is accessible

# --- Dummy hardware functions for your actual electrical instruments ---
def set_vg(voltage):
    print(f"Hardware: Setting V_g to {voltage}V")
    time.sleep(0.1) # Time for voltage to settle

def measure_electrical_data(condition):
    print(f"Hardware: Taking measurement for [{condition}]")
    time.sleep(0.5)
# ---------------------------------------------------------------------

def run_experiment(light_ip, port=5001, cycles=3):
    print(f"Connecting to Light Computer at {light_ip}...")
    conn = Connection.connect(light_ip, port)
    
    try:
        for i in range(cycles):
            print(f"\n--- Cycle {i+1} ---")
            
            # 1. Vg = -1 (Dark)
            set_vg(-1)
            measure_electrical_data("Vg=-1")
            
            # 2. Vg = 1 (Dark)
            set_vg(1)
            measure_electrical_data("Vg=1")
            
            # 3. Light ON
            print("Sending LIGHT ON command...")
            conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": 1})
            conn.receive_json()  # CRITICAL: Wait here until Light PC finishes clicking
            measure_electrical_data("Light ON")
            
            # 4. Light OFF
            print("Sending LIGHT OFF command...")
            conn.send_json({"channel": 6, "on": 1})
            conn.receive_json()  # CRITICAL: Wait here until Light PC finishes clicking
            measure_electrical_data("Light OFF")
            
    finally:
        conn.close()
        print("Experiment complete.")

if __name__ == "__main__":
    run_experiment("192.168.50.17") # Replace with Light PC's IP address