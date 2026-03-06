import time
import csv
import threading
import matplotlib.pyplot as plt

from keithley.keithley import Keithley2636B
from LabAuto.network import Connection

class LaserController:

    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)
        self.lock = threading.Lock()  # prevent concurrent socket use

    def _send(self, payload):
        with self.lock:
            self.conn.send_json(payload)
            return self.conn.receive_json()

    def send_async(self, payload):
        t = threading.Thread(target=self._send, args=(payload,), daemon=True)
        t.start()

    def set_wavelength(self, channel, wavelength, async_mode=False):
        cmd = {"channel": int(channel), "wavelength": str(wavelength)}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def set_power(self, channel, power, async_mode=False):
        cmd = {"channel": int(channel), "power": str(power)}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def toggle_light(self, channel, async_mode=False):
        # Press ON/OFF button to toggle light
        cmd = {"channel": int(channel), "on": 1}
        if async_mode:
            self.send_async(cmd)
        else:
            self._send(cmd)

    def close(self):
        self.conn.close()

class TimeDepExperiment:

    def __init__(self, resource_id, laser_ip, laser_channel, Vd_const=1.0):

        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.laser_channel = laser_channel
        self.Vd_const = Vd_const

        # Instruments
        self.k = None
        self.laser = None

        # Measurement state
        self.current_light_state = 0
        self.start_time = None

        # Plotting
        self.fig = None
        self.axes = None
        self.lines = None

        # Data storage for plotting
        self.times = []
        self.I_Ds = []
        self.I_Gs = []
        self.V_Ds = []
        self.V_Gs = []

    def init_laser(self):
        self.laser = LaserController(self.laser_ip)

    def disconnect_light_PC(self):

        print("Disconnecting light PC...")

        try:
            if self.current_light_state == 1 and self.laser is not None:
                # if light is on, press the on_button again to turn it off
                print("Turning light OFF before exit")
                self.laser.toggle_light(self.laser_channel, async_mode=False)
                time.sleep(2)

        except Exception:
            pass

        finally:
            if self.laser:
                self.laser.close()

    def init_keithley(self):

        print("Connecting to Keithley...")
        self.k = Keithley2636B(self.resource_id)

        self.k.connect()
        self.k.clean_instrument()
        self.k.config()

        self.k.set_nplc('a', "1.0")
        self.k.set_nplc('b', "1.0")

        self.k.enable_output('a', True)
        self.k.enable_output('b', True)

        self.k.set_Vd(self.Vd_const)

    def shutdown_keithley(self):

        if self.k:
            self.k.shutdown()

    def setup_plot(self):

        plt.ion()

        self.fig = plt.figure(figsize=(10, 7))

        '''
        ax1 = Id
        ax2 = Ig
        ax1_v = Vd
        ax2_v = Vg
        '''
        ax1 = self.fig.add_subplot(211)
        ax2 = self.fig.add_subplot(212, sharex=ax1)

        ax1_v = ax1.twinx()
        ax2_v = ax2.twinx()

        ax1.set_ylabel("Id (A)")
        ax2.set_ylabel("Ig (A)")
        ax2.set_xlabel("Time (s)")

        ax1_v.set_ylabel("Vd (V)")
        ax2_v.set_ylabel("Vg (V)")

        line_id, = ax1.plot([], [], 'b.-')
        line_ig, = ax2.plot([], [], 'r.-')
        line_vd, = ax1_v.plot([], [], 'g.-', alpha=0.3)
        line_vg, = ax2_v.plot([], [], 'k.-', alpha=0.3)

        self.axes = (ax1, ax2, ax1_v, ax2_v)
        self.lines = (line_id, line_ig, line_vd, line_vg)

    def update_plot(self):

        line_id, line_ig, line_vd, line_vg = self.lines

        line_id.set_data(self.times, self.I_Ds)
        line_ig.set_data(self.times, self.I_Gs)
        line_vd.set_data(self.times, self.V_Ds)
        line_vg.set_data(self.times, self.V_Gs)

        for ax in self.axes:
            ax.relim()
            ax.autoscale_view()

        plt.pause(0.001) # plt.pause(0.001) = adds 1 ms delay per loop.

    def switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None):
        """Set Vg, then optionally send two-step laser commands"""
        self.k.set_Vg(target_vg)

        if laser_cmd1: # set laser channel, wavelength, power
            channel = laser_cmd1.get("channel", self.laser_channel)
            power = laser_cmd1.get("power", None)
            wavelength = laser_cmd1.get("wavelength", None)
            if power:
                self.laser.set_power(channel, power, async_mode=True)
            if wavelength:
                self.laser.set_wavelength(channel, wavelength, async_mode=True)

        if laser_cmd2: # toggle light on / off
            channel = laser_cmd2.get("channel", self.laser_channel)
            self.laser.toggle_light(channel, async_mode=True)
            self.current_light_state = 1 - self.current_light_state

    def measure_step(self, duration, target_vg, writer):
        """Measure for the given duration and write each point to CSV"""
        step_end = time.time() + duration
        while time.time() < step_end:
            t = time.time() - self.start_time
            I_D, I_G = self.k.measure()
            if I_D is None:
                continue

            # Store for plotting
            self.times.append(t)
            self.I_Ds.append(I_D)
            self.I_Gs.append(I_G)
            self.V_Ds.append(self.Vd_const)
            self.V_Gs.append(target_vg)

            # Write to CSV
            writer.writerow([t, self.Vd_const, target_vg, I_D, I_G, self.current_light_state])

            # Update live plot
            self.update_plot()

    def run(self, sequence, filename, max_retries=3):
        self.setup_plot()

        for attempt in range(max_retries):
            print(f"\n=== Attempt {attempt+1} / {max_retries} ===")
            try:
                self.init_keithley()
                self.init_laser()
                self.start_time = time.time()

                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"])

                    for step_idx, step in enumerate(sequence):
                        target_vg = step["Vg"]
                        duration = step["duration"]
                        laser_cmd1 = step.get("laser_cmd1", None)
                        laser_cmd2 = step.get("laser_cmd2", None)

                        print(f"Step {step_idx+1}: Vg={target_vg}, duration={duration}, laser_cmd1={laser_cmd1}, laser_cmd2={laser_cmd2}")
                        self.switch_source(target_vg, laser_cmd1, laser_cmd2)
                        self.measure_step(duration, target_vg, writer)

                print("Sequence completed successfully!")
                break

            except Exception as e:
                print(f"ERROR: {e}")
                if attempt < max_retries-1:
                    print("Retrying...")
                    time.sleep(3)
                else:
                    print("Max retries reached. Measurement failed.")

            finally:
                self.disconnect_light_PC()
                self.shutdown_keithley()

        plt.ioff()
        plt.show()

if __name__ == "__main__":

    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LASER_IP = "192.168.50.17"
    LASER_CHANNEL = 6

    exp = TimeDepExperiment(RESOURCE_ID, LASER_IP, LASER_CHANNEL, Vd_const=1.0)

    # sequence = [
    #     {"Vg": -1.5, "duration": 3},
    #     {"Vg": 0.5, "duration": 3, 
    #      "laser_cmd1": {"channel": 6, "power": 50, "wavelength": 532}},  # set power/wavelength
    #     {"Vg": 0.5, "duration": 5, 
    #      "laser_cmd2": {"channel": 6}},  # press on_button
    #     {"Vg": 0.5, "duration": 3, 
    #      "laser_cmd2": {"channel": 6}},  # press on_button again if needed
    # ]

    # exp.run(sequence, "time_dep_laser.csv")