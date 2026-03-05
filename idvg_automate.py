import time
import csv
import numpy as np
import matplotlib.pyplot as plt

# Using your existing hardware classes
from keithley.keithley import Keithley2636B #
from LabAuto.network import Connection #

def set_plot():
    plt.ion()  # Turn on interactive mode
    fig, ax1 = plt.subplots(figsize=(8, 6))

    ax1.set_title(f"Live Id-Vg Sweep")
    ax1.set_ylabel("Drain Current (A) - Log", color='b')
    ax1.set_xlabel("Gate Voltage (V)")
    ax1.set_yscale('log')
    ax1.grid(True, which="both", ls="--", alpha=0.5)

    # Create empty line that we will update during the sweep
    line_id, = ax1.plot([], [], 'b.-', markersize=8, label='I_D')
    ax1.legend()
    return fig, ax1, line_id

def prepare_light_on(conn, channel, wavelength, power, light_time):
    print("\nSending Light ON command...")
    conn.send_json({"channel": channel, "wavelength": wavelength, "power": power, "on": 1}) #
    conn.receive_json() # Wait for confirmation

    print(f"Light is ON. Waiting {light_time} seconds for stabilization...")
    for i in range(light_time, 0, -1):
        print(f"  Stabilizing... {i}s remaining", end='\r')
        time.sleep(1) # This pauses the script, no threads needed
    print("\nStabilization complete. Starting Sweep.")

def dark_wait(dark_time):
    print(f"Waiting {dark_time} seconds for stabilization...")
    for i in range(dark_time, 0, -1):
        print(f"  Stabilizing... {i}s remaining", end='\r')
        time.sleep(1) # This pauses the script, no threads needed
    print("\nStabilization complete. Starting Sweep.")

def id_vg(k, gate_start, gate_stop, Vd_target, num_points, filename, ax1, line_id):
    vgs, ids = [], []
    
    settle_delay = 0.1 #
    vg_points = np.linspace(gate_start, gate_stop, num_points) #

    k.enable_output('a', True) #
    k.enable_output('b', True) #
    k.set_Vd(Vd_target) #
    k.set_Vg(gate_start) #
    k.set_autorange('a', 1)
    k.set_autorange('b', 1)
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
                f.flush() ###
                # Update plot arrays
                vgs.append(vg)
                ids.append(abs(I_D))
                
                # Push new data to the live plot
                line_id.set_data(vgs, ids)
                ax1.relim()           # Recalculate limits
                ax1.autoscale_view()  # Rescale axes
                
                # CRITICAL: This allows matplotlib to draw the frame!
                plt.pause(0.01)

def run_id_vg_dark(resource_id,
                    gate_start, gate_stop, num_points, Vd_target, dark_time, filename):
    print("--- Starting Automated Id-Vg Sequence ---")
    # set up plot
    fig, ax1, line_id = set_plot()

    # init hardware and csv file
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["V_D", "V_G", "I_D", "I_G"])
        
    print("Connecting to Keithley...")
    k = Keithley2636B(resource_id) #
    k.connect() #
    k.clean_instrument() #
    k.config() #
    
    k.keithley.write("smua.measure.nplc = 8.0") #
    k.keithley.write("smub.measure.nplc = 8.0") #

    dark_wait(dark_time)
    try:

        id_vg(k, gate_start, gate_stop, Vd_target, num_points, filename, ax1, line_id)
        

    except Exception as e:
        print(f"\nERROR: Sequence interrupted! {e}")
        
    finally:
            
        k.shutdown() #
        print("Hardware safely disabled.")

        # Keep the final plot window open so you can look at it
        plt.ioff() # Turn off interactive mode
        plt.show() # Block the script from exiting until you close the graph window

def run_id_vg_light(resource_id, light_ip, channel, wavelength, power, 
                           gate_start, gate_stop, num_points, Vd_target, dark_time, light_time, filename):
    print("--- Starting Automated Id-Vg Sequence ---")
    # set up plot
    fig, ax1, line_id = set_plot()

    # init hardware and csv file
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

    dark_wait(dark_time)
    try:
        # light on
        prepare_light_on(conn, channel, wavelength, power, light_time)

        id_vg(k, gate_start, gate_stop, Vd_target, num_points, filename, ax1, line_id)
        

    except Exception as e:
        print(f"\nERROR: Sequence interrupted! {e}")
        
    finally:
        print("\n\nSequence Finished. Turning Light OFF...")
        try:
            conn.send_json({"channel": channel, "on": 1}) #
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
    device_number = ''
    run = 0
    FILENAME = f"idvg_{device_number}_{run}'.csv"
    
    power = 10

    run_id_vg_dark(
    resource_id=RESOURCE_ID,
    gate_start=-3.0,
    gate_stop=3.0,
    num_points=51,
    Vd_target=1.0,
    dark_time=0,
    filename=FILENAME
    )
    run_id_vg_light(
    resource_id=RESOURCE_ID,
    light_ip=LIGHT_IP,
    channel=6,
    wavelength=660,
    power=power,
    gate_start=-3.0,
    gate_stop=3.0,
    num_points=51,
    Vd_target=1.0,
    dark_time=0,
    light_time=10,
    filename=FILENAME
    )