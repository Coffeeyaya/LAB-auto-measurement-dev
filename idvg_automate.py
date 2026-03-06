import time
import csv
import numpy as np
import matplotlib.pyplot as plt

from keithley.keithley import Keithley2636B
from laser_remote import LaserController

class IdVgExperiment:
    def __init__(self, resource_id, laser_ip=None):
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        
        # Hardware
        self.k = None
        self.laser = None
        self.light_is_on = False
        self.current_channel = None
        
        # Plotting
        self.fig = None
        self.ax1 = None
        self.current_line = None
        self.vgs = []
        self.ids = []

    def init_hardware(self):
        print("Connecting to Keithley...")
        self.k = Keithley2636B(self.resource_id)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()
        
        # Set NPLC to 8.0 for slower, lower-noise measurements
        self.k.keithley.write("smua.measure.nplc = 8.0")
        self.k.keithley.write("smub.measure.nplc = 8.0")

        if self.laser_ip:
            print(f"Connecting to Light PC at {self.laser_ip}...")
            self.laser = LaserController(self.laser_ip)

    def shutdown_hardware(self):
        print("\nShutting down hardware...")
        try:
            # Safely turn off the light if it was left on
            if self.light_is_on and self.laser and self.current_channel is not None:
                print(f"Turning light OFF on channel {self.current_channel} before exit...")
                self.laser.toggle_light(self.current_channel, async_mode=False)
                time.sleep(2)
        except Exception as e:
            print(f"Error shutting down laser: {e}")
        finally:
            if self.laser:
                self.laser.close()
                
        if self.k:
            self.k.shutdown()
        print("Hardware safely disabled.")

    def setup_plot(self):
        plt.ion()
        self.fig, self.ax1 = plt.subplots(figsize=(8, 6))

        self.ax1.set_title("Live Id-Vg Transfer Characteristics")
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

    def prepare_light(self, laser_cmd, wait_time):
        """Sets laser parameters, turns it on, and waits for stabilization using the shared LaserController."""
        ch = laser_cmd.get("channel")
        wl = laser_cmd.get("wavelength")
        pwr = laser_cmd.get("power")
        
        self.current_channel = ch
        
        print(f"\nConfiguring Light (Ch:{ch}, Wl:{wl}, Pwr:{pwr})...")
        
        # Match the Time-Dependent LaserController API exactly
        if pwr is not None:
            self.laser.set_power(ch, pwr, async_mode=False)
        if wl is not None:
            self.laser.set_wavelength(ch, wl, async_mode=False)
            
        print("Turning Light ON...")
        self.laser.toggle_light(ch, async_mode=False)
        self.light_is_on = True
        
        print(f"Waiting {wait_time}s for light stabilization...")
        for i in range(wait_time, 0, -1):
            print(f"  {i}s remaining", end='\r')
            time.sleep(1)
        print("\nStabilization complete.")

    def dark_wait(self, wait_time):
        if wait_time <= 0: return
        print(f"\nWaiting {wait_time}s for dark stabilization...")
        for i in range(wait_time, 0, -1):
            print(f"  {i}s remaining", end='\r')
            time.sleep(1)
        print("\nStabilization complete.")

    def execute_sweep(self, step_config, writer):
        # Unpack sweep parameters
        Vd = step_config["Vd"]
        start = step_config["start"]
        stop = step_config["stop"]
        points = step_config["points"]
        label = step_config["label"]
        
        vg_points = np.linspace(start, stop, points)
        self.vgs.clear()
        self.ids.clear()

        # Set up a new line on the plot for this sweep
        self.current_line, = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.ax1.legend()

        # Configure Keithley for sweep
        self.k.enable_output('a', True)
        self.k.enable_output('b', True)
        self.k.set_Vd(Vd)
        self.k.set_Vg(start)
        self.k.set_autorange('a', 1)
        self.k.set_autorange('b', 1)
        time.sleep(1) # Initial settle

        print(f"\n--- Starting Sweep: {label} ---")
        for vg in vg_points:
            self.k.set_Vg(vg)
            time.sleep(0.1) # Wait for RC settling
            I_D, I_G = self.k.measure()
            
            if I_D is not None:
                # Log data
                writer.writerow([label, Vd, vg, I_D, I_G])
                
                # Update plot (using absolute Id for log scale)
                self.vgs.append(vg)
                self.ids.append(abs(I_D))
                
                self.current_line.set_data(self.vgs, self.ids)
                self.ax1.relim()
                self.ax1.autoscale_view()
                plt.pause(0.01)

    def run(self, sequence, filename):
        self.setup_plot()

        try:
            self.init_hardware()
            
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Sweep_Label", "V_D", "V_G", "I_D", "I_G"])
                
                for step in sequence:
                    # Handle light preparation if present in this step
                    if "laser_cmd" in step:
                        self.prepare_light(step["laser_cmd"], step["wait_time"])
                    else:
                        self.dark_wait(step.get("wait_time", 0))

                    # Execute the actual Id-Vg sweep
                    self.execute_sweep(step, writer)

                    # Turn off light after the sweep if it was turned on for this step
                    if self.light_is_on:
                        print(f"Sweep done. Turning Light OFF on channel {self.current_channel}...")
                        self.laser.toggle_light(self.current_channel, async_mode=False)
                        self.light_is_on = False
                        time.sleep(2)

            print("\nSequence completed successfully!")

        except Exception as e:
            print(f"\nERROR: Sequence interrupted! {e}")
            
        finally:
            self.shutdown_hardware()
            plt.ioff()
            plt.show() 

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17"
    FILENAME = "idvg_test_01.csv"
    
    # Define the experiment as a list of configurations
    sequence = [
        {
            "label": "Dark Sweep",
            "wait_time": 0,
            "Vd": 1.0, "start": -3.0, "stop": 3.0, "points": 51
        },
        {
            "label": "Light Sweep (660nm, 10%)",
            "wait_time": 10,
            "laser_cmd": {"channel": 6, "wavelength": 660, "power": 10},
            "Vd": 1.0, "start": -3.0, "stop": 3.0, "points": 51
        }
    ]

    exp = IdVgExperiment(RESOURCE_ID, LIGHT_IP)
    exp.run(sequence, FILENAME)