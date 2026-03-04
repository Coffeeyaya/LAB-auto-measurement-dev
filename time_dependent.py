import time
import csv
import matplotlib.pyplot as plt

# Import your existing hardware modules
from keithley.keithley import Keithley2636B #
from LabAuto.network import Connection #

def run_sequential_time_dep(resource_id, light_ip, filename, sequence, Vd_target=1.0):
    print("--- Starting Sequential Time-Dependent Measurement ---")

    # ---------------------------------------------------------
    # 1. SETUP LIVE PLOT (Headless Interactive Mode)
    # ---------------------------------------------------------
    plt.ion() 
    fig = plt.figure(figsize=(10, 7)) #
    
    ax1 = fig.add_subplot(211) #
    ax2 = fig.add_subplot(212, sharex=ax1) #
    ax1.set_ylabel("I_D (A)", color='blue') #
    ax2.set_ylabel("I_G (A)", color='red') #
    ax2.set_xlabel("Time (s)") #
    
    ax1_v = ax1.twinx() #
    ax2_v = ax2.twinx() #
    ax1_v.set_ylabel('V_D (V)', color='green') #
    ax2_v.set_ylabel('V_G (V)', color='black') #

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
        writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"]) #

    print(f"Connecting to Light PC at {light_ip}...")
    conn = Connection.connect(light_ip, 5001) #
    current_light_state = 0 # Track to avoid redundant network commands
    
    print("Connecting to Keithley...")
    k = Keithley2636B(resource_id) #
    k.connect() #
    k.clean_instrument() #
    k.config() #
    
    # 1.0 NPLC for fast ~10Hz measurements
    k.keithley.write("smua.measure.nplc = 1.0") #
    k.keithley.write("smub.measure.nplc = 1.0") #
    
    k.set_Vd(Vd_target) #
    k.enable_output('a', True) #
    k.enable_output('b', True) #

    start_time = time.time() #

    try:
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # ---------------------------------------------------------
            # 3. SEQUENTIAL STATE MACHINE
            # ---------------------------------------------------------
            for step_idx, (target_vg, target_light, duration) in enumerate(sequence):
                print(f"\n--- Sequence Step {step_idx + 1}/{len(sequence)} ---")
                print(f"Applying: Vg = {target_vg}V | Light = {'ON' if target_light else 'OFF'} | Duration = {duration}s")
                
                # Apply Vg
                k.set_Vg(target_vg) #
                
                # Apply Light (Only send command if state needs to change)
                if target_light != current_light_state:
                    cmd_state = 1 if target_light else 0
                    print(f"Sending Light {'ON' if cmd_state else 'OFF'} command...")
                    conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": cmd_state}) #
                    conn.receive_json() # Wait for GUI click to finish
                    current_light_state = target_light

                # Measure continuously for the specified duration
                step_end_time = time.time() + duration
                
                while time.time() < step_end_time:
                    t_elapsed = time.time() - start_time #
                    I_D, I_G = k.measure() #
                    
                    if I_D is not None:
                        # 1. Save Data
                        writer.writerow([t_elapsed, Vd_target, target_vg, I_D, I_G, current_light_state]) 
                        
                        # 2. Update Memory
                        times.append(t_elapsed) #
                        V_Ds.append(Vd_target) 
                        V_Gs.append(target_vg) 
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
                        
                        # 5. Flush GUI events
                        plt.pause(0.001) 
                        
                        print(f"Time: {t_elapsed:.1f}s | Vg: {target_vg}V | Id: {I_D:.2e}A", end='\r')

    except Exception as e:
        print(f"\nERROR: Sequence interrupted! {e}")
        
    finally:
        # ---------------------------------------------------------
        # 4. SAFE SHUTDOWN
        # ---------------------------------------------------------
        print("\n\nSequence Finished. Shutting down...")
        
        try:
            if current_light_state == 1:
                print("Turning Light OFF...")
                conn.send_json({"channel": 6, "on": 0}) #
                conn.receive_json() #
        except Exception:
            pass
        finally:
            conn.close() #
            
        k.shutdown() #
        print("Hardware safely disabled.")

        plt.ioff() 
        plt.show() 

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" #
    LIGHT_IP = "192.168.50.17"
    FILENAME = "automated_sequence.csv"
    
    # Define your exact progression here: (Vg_Voltage, Light_ON_or_OFF, Duration_in_Seconds)
    # 0 = OFF, 1 = ON
    my_sequence = [
        (0.0,  0, 10.0),  # vg = 0, light off, measure for 10 seconds
        (1.0,  0, 10.0),  # vg = 1, light off, measure for 10 seconds
        (1.0,  1, 20.0),  # vg = 1, light ON, measure for 20 seconds
        (1.0,  0, 15.0),  # vg = 1, light off, measure for 15 seconds
        (-1.0, 0, 10.0),  # vg = -1, light off, measure for 10 seconds
        (0.0,  0, 10.0)   # vg = 0, light off, measure for 10 seconds
    ]
    
    run_sequential_time_dep(RESOURCE_ID, LIGHT_IP, FILENAME, sequence=my_sequence, Vd_target=1.0)