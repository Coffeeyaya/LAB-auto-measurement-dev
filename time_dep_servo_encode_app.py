import sys
import time
import csv
import json
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pathlib import Path

from keithley.keithley import Keithley2636B
from LabAuto.laser_remote import LaserController
from servo import ServoController

def get_pp_exact(power_table, wavelength, power_nw):
    try:
        return float(power_table.loc[int(wavelength), str(power_nw)])
    except KeyError:
        print(f"Warning: Cannot convert {power_nw}nW to PP for {wavelength}nm.")
        return None

# --- THE NEW ENCODER BLOCK ---
def encode_binary_block(power_table, channel_idx, wavelength, target_power, vg_on, vg_off, bit_duration, binary_string):
    """
    Translates a string of 1s and 0s into a hardware measurement sequence.
    1 = Vg ON + Light ON
    0 = Vg ON + Light OFF
    """
    pp = get_pp_exact(power_table, wavelength, target_power)
    sequence_steps = []
    
    # 1. Start with a baseline rest period to stabilize the device
    # (Using 3x the bit duration to clearly mark the start of a transmission)
    # sequence_steps.append({"Vg": vg_off, "duration": bit_duration * 3}) 
    
    # 2. Configure the Laser Power ONCE before the transmission starts
    sequence_steps.append({"Vg": vg_off, "duration": 5, "laser_cmd1": {"channel": channel_idx, "power": pp}})
    sequence_steps.append({"Vg": vg_off, "duration": 5, "laser_cmd2": {"channel": channel_idx, "on": 1}})
    
    # 3. Loop through every character in your string
    for bit in str(binary_string):
        
        if bit == '1':
            # Bit 1: Apply Vg AND turn on the Light
            step1 = {
                "Vg": vg_on, 
                "duration": bit_duration, 
                # "laser_cmd3": {"channel": channel_idx, "on": 1} 
            }
            step2 = {
                "Vg": vg_on, 
                "duration": bit_duration,
                "laser_cmd3": {"channel": channel_idx, "on": 1}
            }
            step3 = {
                "Vg": vg_on, 
                "duration": bit_duration,
                "laser_cmd3": {"channel": channel_idx, "on": 1}
            }
            sequence_steps.append(step1)
            sequence_steps.append(step2)
        elif bit == '0':
            # Bit 0: Apply Vg, but keep the Light OFF
            step = {
                "Vg": vg_on, 
                "duration": bit_duration,
                # "laser_cmd3": {"channel": channel_idx, "on": 0} 
            }
            sequence_steps.append(step)
        else:
            continue # Ignore spaces or invalid characters
            
        # sequence_steps.append(step)
        
        # --- THE RETURN-TO-ZERO (REST) STATE ---
        # Turn everything off for half a bit-duration so consecutive 
        # 11s or 00s don't visually merge together.
        rest_step = {
            "Vg": vg_off,
            "duration": bit_duration,
            # "laser_cmd2": {"channel": channel_idx, "on": 0}
        }
        sequence_steps.append(rest_step)
    sequence_steps.append({"Vg": vg_off, "duration": 5, "laser_cmd2": {"channel": channel_idx, "on": 1}})
    return sequence_steps

# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class TimeDepWorker(QThread):
    new_config = pyqtSignal(int, str)
    new_data = pyqtSignal(int, float, float, float, float, float)
    status_update = pyqtSignal(str) 
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser, servo, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.laser = laser
        self.servo = servo
        self.config_files = config_files_list
        
        self.k = None
        self.current_light_state = 0 
        self.servo_state = 0 
        self.laser_channel = None
        self.running = True
        self.current_applied_vg = None

    def switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None):
        if target_vg != self.current_applied_vg:
            self.k.set_Vg(target_vg)
            self.current_applied_vg = target_vg

        if laser_cmd1: 
            self.status_update.emit("Configuring laser...")
            self.laser.send_cmd(laser_cmd1, wait_for_reply=False) 
        if laser_cmd2: 
            self.status_update.emit("Toggling laser ON/OFF...")
            self.laser_channel = laser_cmd2["channel"]
            self.laser.send_cmd(laser_cmd2, wait_for_reply=False) 
            # We track the intent of the light state so our CSV file knows what's happening
            self.current_light_state = laser_cmd2["on"] 
        if laser_cmd3:
            self.status_update.emit("Toggling Physical Shutter...")
            if self.servo:
                self.servo.toggle_light() 
            self.servo_state = 1 - self.servo_state

    def run(self):
        try:
            self.status_update.emit("Initializing Keithley...")
            self.k = Keithley2636B(self.resource_id)
            self.k.connect()
            self.k.clean_instrument()
            self.k.config()

            power_table_path = Path("calibration") / "pp_df.csv"
            if power_table_path.exists():
                power_table = pd.read_csv(power_table_path, index_col=0)
            else:
                self.status_update.emit("Warning: Power table CSV not found!")
                power_table = None

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break

                self.k.set_auto_zero_once()
                
                self.status_update.emit(f"Loading config: {config_file}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                wait_time = params.get("wait_time", 0)
                for i in range(wait_time, 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Wait ... {i}s")
                    time.sleep(1)

                output_dir = Path("data")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                device_num = params.get('device_number', '0')
                run_num = int(params.get('run_number', 1))
                
                filename = output_dir / f"encoded_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"encoded_{device_num}_{run_num}_config.json"
                
                if filename.exists() or config_backup.exists():
                    error_msg = f"FILE EXISTS ERROR: {filename.name} already exists. Stopping experiment to prevent overwrite!"
                    print(error_msg)
                    self.status_update.emit(error_msg)
                    self.running = False
                    break 
                
                with open(config_backup, "w") as f_back:
                    json.dump(params, f_back, indent=4)

                self.k.set_nplc('a', params["nplc_a"])
                self.k.set_nplc('b', params["nplc_b"])
                self.k.set_limit('a', params["current_limit_a"])
                self.k.set_limit('b', params["current_limit_b"])
                self.k.set_range('a', params["current_range_a"])
                self.k.set_range('b', params["current_range_b"])
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)
                
                vd_const = float(params["vd_const"])
                self.k.set_Vd(vd_const)
                
                label = params.get("label", f"Run {run_num}")
                self.new_config.emit(config_idx, label) 

                ### BUILD THE ENCODED SEQUENCE
                sequence = []
                channel_arr = np.array(params.get("channel_arr", [6])).astype(int).astype(str)
                wavelength_arr = np.array(params.get("wavelength_arr", [660])).astype(int)
                power_arr = np.array(params.get("power_arr", [100])).astype(int).astype(str)
                
                # Retrieve the binary string and bit duration from the JSON config
                binary_string = params.get("binary_string", "1010")
                bit_duration = params.get("bit_duration", 1.0) 

                # For the encoder, we only run the first channel/wavelength in the array
                ch_idx = channel_arr[0]
                wl = wavelength_arr[0]
                power = power_arr[0]
                
                unit = encode_binary_block(
                    power_table, ch_idx, wl, power,
                    params["vg_on"], params["vg_off"], 
                    bit_duration, binary_string
                )
                sequence.extend(unit)
                    
                # Final rest state
                sequence.extend([{"Vg": params['vg_off'], "duration": 2.0}])

                start_time = time.time()
                with open(filename, 'w', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State", "Servo_State"])

                    for step_idx, step in enumerate(sequence):
                        if not self.running: break

                        target_vg = step["Vg"]
                        duration = step["duration"]
                        
                        self.switch_source(target_vg, step.get("laser_cmd1"), step.get("laser_cmd2"), step.get("laser_cmd3"))

                        step_end = time.time() + duration
                        self.status_update.emit(f"[{label}] Transmitting Bit {step_idx+1}/{len(sequence)}: Measuring...")
                        
                        last_emit_time = time.time()
                        
                        while time.time() < step_end:
                            if not self.running: break

                            # --- BUG FIX: THE TIME DRIFT BUFFER ---
                            # Measure FIRST, then sleep if we are out of time. 
                            # If we sleep first and then break, we miss the final measurement of the pulse!
                            reading = self.k.measure()
                            
                            if reading is not None and len(reading) == 2:
                                I_D, I_G = reading 
                                if I_D is not None:
                                    t = time.time() - start_time
                                    writer.writerow([t, vd_const, target_vg, I_D, I_G, self.current_light_state, self.servo_state])

                                    current_t = time.time()
                                    if current_t - last_emit_time > 0.1: # Increased refresh rate to 10Hz for fast pulses
                                        self.new_data.emit(config_idx, t, vd_const, target_vg, I_D, I_G)
                                        last_emit_time = current_t
                                        
                            # After a successful measurement, check if there is enough time 
                            # left in the step for another 40ms Keithley sweep. If not, sleep.
                            time_left = step_end - time.time()
                            if time_left < 0.05:
                                if time_left > 0:
                                    time.sleep(time_left)
                                break 

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self.status_update.emit("Transmission complete. Shutting down hardware...")

            if self.servo and self.servo.is_on:
                self.servo.toggle_light() 

            if self.laser:
                if self.current_light_state and self.laser_channel is not None:
                    self.laser.send_cmd({"channel": self.laser_channel, "on": 0}, wait_for_reply=False)
                self.laser.close() 
            if self.k:
                self.k.shutdown()
                
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

# -------------------------------
# GUI Window
# -------------------------------
class TimeDepWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Time Dependent measurement")
        self.worker = worker
        
        # store measurement data: {"t": [], "id": [], "ig": [], "vd": [], "vg": []}
        self.data_memory = {}
        self.lines_id = {}
        self.lines_ig = {}
        self.lines_vd = {}
        self.lines_vg = {}

        self.last_draw_time = time.time()

        self._setup_ui()
        
        self.worker.new_config.connect(self.add_config_line)
        # new_data: only sample data every 0.2 seconds, so that there are not too many points when updating plot
        # raw data still collected in csv file, just not plot all of them in real time
        self.worker.new_data.connect(self.update_plot)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.sequence_finished.connect(self.on_finished)
        
        self.worker.start()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.status_label = QLabel("Status: Starting up...")
        self.status_label.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.figure = Figure(figsize=(16, 10))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        self.ax1_v = self.ax1.twinx()
        self.ax2_v = self.ax2.twinx()

        self.ax1.set_ylabel("Id (A)", color='blue')
        self.ax2.set_ylabel("Ig (A)", color='red')
        self.ax2.set_xlabel("Time (s)")
        self.ax1_v.set_ylabel("Vd (V)", color='green')
        self.ax2_v.set_ylabel("Vg (V)", color='black')

    def add_config_line(self, config_idx, label):
        self.data_memory[config_idx] = {"t": [], "id": [], "ig": [], "vd": [], "vg": []}
        
        self.lines_id[config_idx], = self.ax1.plot([], [], '.-', label=f'Id ({label})')
        self.lines_ig[config_idx], = self.ax2.plot([], [], '.-', label=f'Ig ({label})')
        self.lines_vd[config_idx], = self.ax1_v.plot([], [], '', alpha=0.3)
        self.lines_vg[config_idx], = self.ax2_v.plot([], [], '', alpha=0.3)
        
        self.ax1.legend(loc='best')
        self.ax2.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, config_idx, t, Vd, Vg, I_D, I_G):
        mem = self.data_memory[config_idx]
        mem["t"].append(t)
        mem["vd"].append(Vd)
        mem["vg"].append(Vg)
        mem["id"].append(I_D)
        mem["ig"].append(I_G)
        
        self.lines_id[config_idx].set_data(mem["t"], mem["id"])
        self.lines_ig[config_idx].set_data(mem["t"], mem["ig"])
        self.lines_vd[config_idx].set_data(mem["t"], mem["vd"])
        self.lines_vg[config_idx].set_data(mem["t"], mem["vg"])
        
        current_time = time.time()
        if current_time - self.last_draw_time > 0.2:
            for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
                ax.relim()
                ax.autoscale_view()
            self.canvas.draw()
            self.last_draw_time = current_time

    def on_finished(self):
        for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
            ax.relim()
            ax.autoscale_view()
        self.canvas.draw()
        
        # Check if it finished due to an existing file or naturally
        if "FILE EXISTS ERROR" not in self.status_label.text():
            self.status_label.setText("Batch Sequence Finished. Hardware is safe.")

    def closeEvent(self, event): 
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LASER_IP = "10.0.0.2"

    print("Connecting to Laser PC...")
    laser = LaserController(LASER_IP)
    print("Laser connected.")

    print("Connecting to Servo Shutter...")
    try:
        servo = ServoController() # Your class that handles the auto-port connection
        print("Servo connected.")
    except Exception as e:
        print(f"Warning: Could not connect to servo ({e}). Running without physical shutter.")
        servo = None

    config_dir = Path("config")
    config_queue = [
        config_dir / "time_dependent_config_encode_app.json",
        # config_dir / "time_dependent_config_2.json",
        # config_dir / "time_dependent_config_3.json"
    ]

    app = QApplication(sys.argv)
    
    worker = TimeDepWorker(RESOURCE_ID, laser, servo, config_queue)
    window = TimeDepWindow(worker)
    window.show()

    sys.exit(app.exec_())