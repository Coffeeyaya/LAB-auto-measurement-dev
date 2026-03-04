import time
import csv
import numpy as np
import matplotlib.pyplot as plt

# Using your existing hardware classes
from keithley.keithley import Keithley2636B #
from LabAuto.network import Connection #

def run_automated_sequence(resource_id, light_ip, filename, Vd_target=1.0):
    print("--- Starting Automated Id-Vg Sequence ---")
    
    # ---------------------------------------------------------
    # 1. SETUP PLOT (Interactive Mode)
    # ---------------------------------------------------------
    plt.ion()  # Turn on interactive mode
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    ax1.set_title(f"Live Id-Vg Sweep (Vd = {Vd_target}V)")
    ax1.set_ylabel("Drain Current (A) - Log", color='b')
    ax1.set_xlabel("Gate Voltage (V)")
    ax1.set_yscale('log')
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    
    # Create empty line that we will update during the sweep
    line_id, = ax1.plot([], [], 'b.-', markersize=8, label='I_D')
    ax1.legend()
    
    # ---------------------------------------------------------
    # 2. INITIALIZE HARDWARE & FILES
    # ---------------------------------------------------------
    vgs, ids = [], []
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["V_D", "V_G", "I_D", "I_G"])

    print(f"Connecting to Light PC at {light_ip}...")
    conn = Connection.connect(light_ip, 5001) #
    
    print("Connecting to Keithley...")
    k = Keithley2636B(resource_id) #
    k.connect() #
    k.clean_instrument() #
    k.config() #
    
    k.keithley.write("smua.measure.nplc = 8.0") #
    k.keithley.write("smub.measure.nplc = 8.0") #

    try:
        # ---------------------------------------------------------
        # 3. LIGHT ON & WAIT (Standard single-thread loop)
        # ---------------------------------------------------------
        print("\nSending Light ON command...")
        conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": 1}) #
        conn.receive_json() # Wait for confirmation
        
        print("Light is ON. Waiting 30 seconds for stabilization...")
        for i in range(30, 0, -1):
            print(f"  Stabilizing... {i}s remaining", end='\r')
            time.sleep(1) # This pauses the script, no threads needed
        print("\nStabilization complete. Starting Sweep.")

        # ---------------------------------------------------------
        # 4. START ID-VG SWEEP
        # ---------------------------------------------------------
        gate_start = -3.0 #
        gate_stop = 3.0 #
        steps = 101 #
        settle_delay = 0.1 #
        vg_points = np.linspace(gate_start, gate_stop, steps) #

        k.set_Vd(Vd_target) #
        k.set_Vg(gate_start) #
        k.enable_output('a', True) #
        k.enable_output('b', True) #
        time.sleep(1) # Initial settle

        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            
            for vg in vg_points:
                k.set_Vg(vg) #
                time.sleep(settle_delay) # Wait for RC settling
                I_D, I_G = k.measure() #
                
                if I_D is not None:
                    # Save data
                    writer.writerow([Vd_target, vg, I_D, I_G]) #
                    
                    # Update plot arrays
                    vgs.append(vg)
                    ids.append(abs(I_D))
                    
                    # Push new data to the live plot
                    line_id.set_data(vgs, ids)
                    ax1.relim()           # Recalculate limits
                    ax1.autoscale_view()  # Rescale axes
                    
                    # CRITICAL: This allows matplotlib to draw the frame!
                    plt.pause(0.01)       
                    
                    print(f"Measured -> Vg: {vg:.2f}V | I_D: {I_D:.2e}A", end='\r')

    except Exception as e:
        print(f"\nERROR: Sequence interrupted! {e}")
        
    finally:
        # ---------------------------------------------------------
        # 5. SAFE SHUTDOWN
        # ---------------------------------------------------------
        print("\n\nSequence Finished. Turning Light OFF...")
        try:
            conn.send_json({"channel": 6, "on": 0}) #
            conn.receive_json() #
        except Exception as e:
            pass
        finally:
            conn.close() #
            
        k.shutdown() #
        print("Hardware safely disabled.")

        # Keep the final plot window open so you can look at it
        plt.ioff() # Turn off interactive mode
        plt.show() # Block the script from exiting until you close the graph window

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" #
    LIGHT_IP = "192.168.50.17" #
    FILENAME = "automated_idvg_data.csv"
    
    run_automated_sequence(RESOURCE_ID, LIGHT_IP, FILENAME, Vd_target=1.0)