import time
import csv
import threading
import matplotlib.pyplot as plt

from keithley.keithley import Keithley2636B
from LabAuto.network import Connection

class LaserController:
    # Simplified! No locks, no complex async functions needed.
    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)

    def send_cmd(self, payload, wait_for_reply=True):
        self.conn.send_json(payload)
        if wait_for_reply:
            return self.conn.receive_json()

    def close(self):
        self.conn.close()

class TimeDepExperiment:
    def __init__(self, resource_id, laser_ip, laser_channel, Vd_const=1.0):
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.laser_channel = laser_channel
        self.Vd_const = Vd_const

        self.k = None
        self.laser = None
        self.current_light_state = 0
        self.start_time = None
        
        # We need a flag to tell the Matplotlib loop when the sequence is done
        self.is_running = False 

        # Plotting memory
        self.times, self.I_Ds, self.I_Gs, self.V_Ds, self.V_Gs = [], [], [], [], []

    def setup_plot(self):
        plt.ion()
        self.fig = plt.figure(figsize=(10, 7))
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212, sharex=self.ax1)
        self.ax1_v = self.ax1.twinx()
        self.ax2_v = self.ax2.twinx()

        self.ax1.set_ylabel("Id (A)")
        self.ax2.set_ylabel("Ig (A)")
        self.ax2.set_xlabel("Time (s)")

        self.line_id, = self.ax1.plot([], [], 'b.-')
        self.line_ig, = self.ax2.plot([], [], 'r.-')
        self.line_vd, = self.ax1_v.plot([], [], 'g.-', alpha=0.3)
        self.line_vg, = self.ax2_v.plot([], [], 'k.-', alpha=0.3)

    def _measurement_thread_worker(self, sequence, filename):
        """This entirely runs in the background!"""
        try:
            # 1. Init Hardware
            self.k = Keithley2636B(self.resource_id)
            self.k.connect()
            self.k.clean_instrument()
            self.k.config()
            self.k.set_nplc('a', "1.0")
            self.k.set_nplc('b', "1.0")
            self.k.enable_output('a', True)
            self.k.enable_output('b', True)
            self.k.set_Vd(self.Vd_const)

            self.laser = LaserController(self.laser_ip)
            self.start_time = time.time()

            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"])

                # 2. Run Sequence
                for step_idx, step in enumerate(sequence):
                    target_vg = step["Vg"]
                    duration = step["duration"]
                    self.k.set_Vg(target_vg)

                    # --- Safe, Synchronous Laser Setup ---
                    if "laser_cmd1" in step:
                        print("Waiting for Light PC to configure laser...")
                        # This blocks this background thread, but Matplotlib keeps updating!
                        self.laser.send_cmd(step["laser_cmd1"], wait_for_reply=True) 

                    # --- Fire-and-Forget Laser Trigger ---
                    if "laser_cmd2" in step:
                        print("Triggering Light ON/OFF!")
                        # wait_for_reply=False means we instantly start measuring the Keithley
                        self.laser.send_cmd(step["laser_cmd2"], wait_for_reply=False) 
                        self.current_light_state = 1 - self.current_light_state

                    # 3. Fast Polling Loop
                    step_end = time.time() + duration
                    while time.time() < step_end:
                        I_D, I_G = self.k.measure()
                        if I_D is not None:
                            t = time.time() - self.start_time
                            self.times.append(t)
                            self.I_Ds.append(I_D)
                            self.I_Gs.append(I_G)
                            self.V_Ds.append(self.Vd_const)
                            self.V_Gs.append(target_vg)
                            writer.writerow([t, self.Vd_const, target_vg, I_D, I_G, self.current_light_state])
                            
            print("\nSequence completed successfully!")

        except Exception as e:
            print(f"Hardware Error in background thread: {e}")
        finally:
            if self.laser:
                # Clean up
                self.laser.send_cmd({"channel": self.laser_channel, "on": 1}, wait_for_reply=False)
                self.laser.close()
            if self.k:
                self.k.shutdown()
            self.is_running = False # Tell the main thread we are done

    def run(self, sequence, filename):
        self.setup_plot()
        self.is_running = True

        # Kick off the hardware routine in the background
        measure_thread = threading.Thread(
            target=self._measurement_thread_worker, 
            args=(sequence, filename), 
            daemon=True
        )
        measure_thread.start()

        # MAIN THREAD JOB: Just keep the GUI alive and updated!
        while self.is_running:
            # Update data lines
            self.line_id.set_data(self.times, self.I_Ds)
            self.line_ig.set_data(self.times, self.I_Gs)
            self.line_vd.set_data(self.times, self.V_Ds)
            self.line_vg.set_data(self.times, self.V_Gs)

            # Rescale axes
            for ax in (self.ax1, self.ax2, self.ax1_v, self.ax2_v):
                ax.relim()
                ax.autoscale_view()

            # Process GUI events (keeps the window un-frozen)
            plt.pause(0.1) 

        print("Experiment finished. You can now close the plot window.")
        plt.ioff()
        plt.show()


if __name__ == "__main__":

    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LASER_IP = "192.168.50.17"
    LASER_CHANNEL = 6

    exp = TimeDepExperiment(RESOURCE_ID, LASER_IP, LASER_CHANNEL, Vd_const=1.0)

    sequence = [
        {"Vg": -1.5, "duration": 3},
        {"Vg": 0.5, "duration": 3, 
         "laser_cmd1": {"channel": 6, "power": 50, "wavelength": 532}},  # set power/wavelength
        {"Vg": 0.5, "duration": 5, 
         "laser_cmd2": {"channel": 6}},  # press on_button
        {"Vg": 0.5, "duration": 3, 
         "laser_cmd2": {"channel": 6}},  # press on_button again if needed
    ]

    exp.run(sequence, "time_dep_laser.csv")