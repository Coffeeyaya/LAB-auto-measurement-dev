import time
import csv
import pyvisa
import matplotlib.pyplot as plt

# Import your existing modules
from keithley.keithley import Keithley2636B #
from LabAuto.network import Connection #

def run_time_dependent_auto(resource_id, light_ip, filename, total_duration=60.0):
    print("--- Starting Automated Time-Dependent Measurement ---")

    # ---------------------------------------------------------
    # 1. SETUP LIVE PLOT (Headless Interactive Mode)
    # ---------------------------------------------------------
    plt.ion() # Turn on interactive mode for live updates
    fig = plt.figure(figsize=(10, 7)) #
    
    # Setup Left Axes (Current)
    ax1 = fig.add_subplot(211) #
    ax2 = fig.add_subplot(212, sharex=ax1) #
    ax1.set_ylabel("I_D (A)", color='blue') #
    ax2.set_ylabel("I_G (A)", color='red') #
    ax2.set_xlabel("Time (s)") #
    
    # Setup Right Axes (Voltage)
    ax1_v = ax1.twinx() #
    ax2_v = ax2.twinx() #
    ax1_v.set_ylabel('V_D (V)', color='green') #
    ax2_v.set_ylabel('V_G (V)', color='black') #

    # Initialize empty lines
    line_id, = ax1.plot([], [], 'b.-', label='I_D') #
    line_ig, = ax2.plot([], [], 'r.-', label='I_G') #
    line_vd, = ax1_v.plot([], [], 'g.-', alpha=0.3, label='V_D') #
    line_vg, = ax2_v.plot([], [], 'k.-', alpha=0.3, label='V_G') #

    ax1.legend(loc='upper left'); ax2.legend(loc='upper left') #
    ax1_v.legend(loc='upper right'); ax2_v.legend(loc='upper right') #

    # ---------------------------------------------------------
    # 2. INITIALIZE FILES & HARDWARE
    # ---------------------------------------------------------
    times, I_Ds, I_Gs, V_Ds, V_Gs = [], [], [], [], [] #
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"]) #

    print(f"Connecting to Light PC at {light_ip}...")
    conn = Connection.connect(light_ip, 5001) #
    
    print("Connecting to Keithley...")
    k = Keithley2636B(resource_id) #
    k.connect() #
    k.clean_instrument() #
    k.config() #
    
    # Crucial: NPLC = 1.0 allows for fast ~10Hz measurements
    k.keithley.write("smua.measure.nplc = 1.0")  #
    k.keithley.write("smub.measure.nplc = 1.0")  #

    try:
        # ---------------------------------------------------------
        # 3. TURN LIGHT ON
        # ---------------------------------------------------------
        print("\nSending Light ON command...")
        conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": 1}) 
        conn.receive_json() # Wait for GUI click to finish
        print("Light is ON.")

        # ---------------------------------------------------------
        # 4. START VG PULSE & ENABLE OUTPUTS
        # ---------------------------------------------------------
        # Define your pulse sequence: [(Voltage, Duration), ...]
        vg_sequence = [(1.0, 5.0), (-1.0, 5.0), (2.0, 5.0), (-2.0, 5.0)] # Example sequence
        
        k.set_Vd(1.0) # Set constant Vd #
        k.enable_output('a', True) #
        k.enable_output('b', True) #
        
        print("Starting Vg background pulse...")
        k.start_vg_pulse(vg_sequence) # This runs asynchronously in the background

        # ---------------------------------------------------------
        # 5. HIGH-SPEED MEASUREMENT LOOP
        # ---------------------------------------------------------
        print(f"Recording data for {total_duration} seconds...")
        start_time = time.time() #
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            
            while True:
                current_time = time.time()
                t_elapsed = current_time - start_time #
                
                if t_elapsed >= total_duration:
                    break # Stop when the total duration is reached
                
                # Measure current (Vg is being changed automatically by the background thread)
                I_D, I_G = k.measure() #
                
                if I_D is not None:
                    current_vd = k.Vd # Fetch current state
                    current_vg = k.Vg # Fetch current state
                    
                    # 1. Save Data
                    writer.writerow([t_elapsed, current_vd, current_vg, I_D, I_G]) #
                    
                    # 2. Update Memory Arrays
                    times.append(t_elapsed) #
                    V_Ds.append(current_vd) #
                    V_Gs.append(current_vg) #
                    I_Ds.append(I_D) #
                    I_Gs.append(I_G) #
                    
                    # 3. Push to Plot
                    line_id.set_data(times, I_Ds) #
                    line_ig.set_data(times, I_Gs) #
                    line_vd.set_data(times, V_Ds) #
                    line_vg.set_data(times, V_Gs) #
                    
                    # 4. Rescale Axes
                    for ax in [ax1, ax2, ax1_v, ax2_v]: #
                        ax.relim() #
                        ax.autoscale_view() #
                    
                    # 5. Flush GUI events (Allows matplotlib to redraw the window without crashing)
                    plt.pause(0.001) 
                    
                    print(f"Time: {t_elapsed:.1f}s | Vg: {current_vg}V | Id: {I_D:.2e}A", end='\r')

    except Exception as e:
        print(f"\nERROR: Sequence interrupted! {e}")
        
    finally:
        # ---------------------------------------------------------
        # 6. SAFE SHUTDOWN
        # ---------------------------------------------------------
        print("\n\nSequence Finished. Shutting down...")
        
        # Stop the background Vg pulse thread
        k.stop_vg_pulse() #
        
        # Turn Light OFF
        try:
            print("Turning Light OFF...")
            conn.send_json({"channel": 6, "on": 0}) 
            conn.receive_json() 
        except Exception:
            pass
        finally:
            conn.close() #
            
        # Turn off Keithley relays
        k.shutdown() #
        print("Hardware safely disabled.")

        # Keep the final plot window open for review
        plt.ioff() 
        plt.show() 

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" #
    LIGHT_IP = "192.168.50.17"
    FILENAME = "automated_time_dep.csv"
    
    # Run the sequence for 60 seconds
    run_time_dependent_auto(RESOURCE_ID, LIGHT_IP, FILENAME, total_duration=60.0)