import time
import csv
import threading
import matplotlib.pyplot as plt

# Import your existing hardware modules
from keithley.keithley import Keithley2636B #
from LabAuto.network import Connection #

# =============================================================================
# Helper Functions
# =============================================================================

def toggle_light_async(conn, channel):
    """Sends the command and waits for the ACK in the background."""
    try:
        conn.send_json({"channel": channel, "on": 1}) #
        conn.receive_json()
    except Exception as e:
        print(f"\nNetwork Error in background thread: {e}") #

def setup_live_plot():
    """Initializes the matplotlib figure and returns the figure, axes, and lines."""
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

    ax1.legend(loc='upper left')
    ax2.legend(loc='upper left') 
    ax1_v.legend(loc='upper right')
    ax2_v.legend(loc='upper right') 

    axes = (ax1, ax2, ax1_v, ax2_v)
    lines = (line_id, line_ig, line_vd, line_vg)
    return fig, axes, lines

def update_plot(axes, lines, times, I_Ds, I_Gs, V_Ds, V_Gs):
    """Pushes new data to the live plot and rescales the axes."""
    ax1, ax2, ax1_v, ax2_v = axes
    line_id, line_ig, line_vd, line_vg = lines

    line_id.set_data(times, I_Ds) 
    line_ig.set_data(times, I_Gs) 
    line_vd.set_data(times, V_Ds) 
    line_vg.set_data(times, V_Gs) 
    
    for ax in axes: 
        ax.relim() 
        ax.autoscale_view() 
    
    plt.pause(0.001)  # Flush GUI events

def initialize_hardware(resource_id, light_ip, Vd_target):
    """Establishes connections and configures default states."""
    print(f"Connecting to Light PC at {light_ip}...")
    conn = Connection.connect(light_ip, 5001) #
    
    print("Connecting to Keithley...")
    k = Keithley2636B(resource_id) #
    k.connect() 
    k.clean_instrument() 
    k.config() 
    
    k.keithley.write("smua.measure.nplc = 1.0") #
    k.keithley.write("smub.measure.nplc = 1.0") #
    
    k.set_Vd(Vd_target) #
    k.enable_output('a', True) #
    k.enable_output('b', True) #

    return k, conn

def shutdown_hardware(k, conn, current_light_state):
    """Safely powers down relays and resets light state."""
    print("\nShutting down hardware...")
    try:
        # Guarantee the light turns off if we abort mid-illumination
        if current_light_state == 1 and conn is not None:
            print("Executing final GUI click to turn Light OFF...")
            conn.send_json({"channel": 6, "on": 1}) #
            time.sleep(2) # Give it time to execute without needing a blocking receive
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close() #
        
    if k is not None:
        k.shutdown() #
    print("Hardware safely disabled.")

# =============================================================================
# Main Measurement Loop
# =============================================================================

def run_measurement(resource_id, light_ip, filename, channel, sequence, Vd_target=1.0, max_retries=3):
    print("--- Starting Sequential Time-Dependent Measurement ---")

    # Initialize visualization and data storage
    fig, axes, lines = setup_live_plot()
    times, I_Ds, I_Gs, V_Ds, V_Gs = [], [], [], [], [] 
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"]) #

    # --- THE RETRY LOOP ---
    for attempt in range(max_retries):
        print(f"\n=== Attempt {attempt + 1} of {max_retries} ===")
        
        k = None
        conn = None
        current_light_state = 0 #

        try:
            k, conn = initialize_hardware(resource_id, light_ip, Vd_target)
            start_time = time.time() #

            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                
                # --- SEQUENTIAL STATE MACHINE ---
                for step_idx, (target_vg, target_light, duration) in enumerate(sequence):
                    print(f"\n--- Sequence Step {step_idx + 1}/{len(sequence)} ---")
                    print(f"Applying: Vg = {target_vg}V | Light = {'ON' if target_light else 'OFF'} | Duration = {duration}s") #
                    
                    k.set_Vg(target_vg) #
                    
                    # Apply Light Toggle
                    if target_light != current_light_state:
                        print(f"Executing GUI click to toggle light {'ON' if target_light else 'OFF'}...") #
                        threading.Thread(target=toggle_light_async, args=(conn,channel), daemon=True).start() #
                        current_light_state = target_light #

                    # Measure for duration
                    step_end_time = time.time() + duration
                    while time.time() < step_end_time:
                        t_elapsed = time.time() - start_time #
                        I_D, I_G = k.measure() #
                        
                        if I_D is not None:
                            writer.writerow([t_elapsed, Vd_target, target_vg, I_D, I_G, current_light_state]) 
                            
                            times.append(t_elapsed) 
                            V_Ds.append(Vd_target) 
                            V_Gs.append(target_vg) 
                            I_Ds.append(I_D) 
                            I_Gs.append(I_G) 
                            
                            update_plot(axes, lines, times, I_Ds, I_Gs, V_Ds, V_Gs)
                            print(f"Time: {t_elapsed:.1f}s | Vg: {target_vg}V | Id: {I_D:.2e}A", end='\r') #

            # If loop finishes without exceptions, break out of retries
            print("\nSequence completed successfully!")
            break 

        except Exception as e:
            print(f"\nERROR: Sequence interrupted! {e}") #
            if attempt < max_retries - 1:
                print("Preparing to restart the sequence...")
                time.sleep(3) 
            else:
                print("Max retries reached. Measurement failed.")
            
        finally:
            shutdown_hardware(k, conn, current_light_state)

    print("Done.")
    plt.ioff() #
    plt.show() #

# =============================================================================
# Script Execution
# =============================================================================
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" #
    LIGHT_IP = "192.168.50.17" #
    device_number = ''
    run = ''
    FILENAME = f"time_{device_number}_{run}.csv" #
    
    duration = 2 #
    Vg_on = 0.1 #
    Vg_off = -1 #
    channel = 6
    # power = 10
    
    my_sequence = [ #
        (0.0,  0, duration),   #
        (Vg_off,  0, duration),#
        (Vg_on,  0, duration), #
        (Vg_on,  1, duration), # light on
        (Vg_on,  0, duration), # light off
        (Vg_off, 0, duration), #
          #
    ]
    for i in range(5):
        my_sequence.extend([(Vg_on,  0, duration), #
            (Vg_on,  1, duration),
            (Vg_on,  0, duration),
            (Vg_off, 0, duration)])
    my_sequence.append((0, 0, duration))
    
    run_measurement(RESOURCE_ID, LIGHT_IP, FILENAME, channel=channel, sequence=my_sequence, Vd_target=1)