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
from laser_remote import LaserController # Imported perfectly from your module!

def get_pp_exact(df, wavelength, power_nw):
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        return None

def single_power_multi_wavelength_basic_block(power_table, channel_idx, wavelength, target_power, vg_on, vg_off, duration_1, duration_2, duration_3, duration_4):
    pp = get_pp_exact(power_table, wavelength, target_power)
    
    basic_block = [
        {"Vg": vg_off, "duration": duration_1},
        {"Vg": vg_on, "duration": duration_2, "laser_cmd1": {"channel": channel_idx, "power": pp}},
        {"Vg": vg_on, "duration": duration_3, "laser_cmd2": {"channel": channel_idx, "on": 1}}, 
        {"Vg": vg_on, "duration": duration_4, "laser_cmd2": {"channel": channel_idx, "on": 1}}, 
    ]
    return basic_block

# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class TimeDepWorker(QThread):
    new_config = pyqtSignal(int, str) # config_idx, label
    new_data = pyqtSignal(int, float, float, float, float, float) # config_idx, t, Vd, Vg, Id, Ig
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.laser = laser  # Passed directly from main
        self.config_files = config_files_list
        
        self.k = None
        self.current_light_state = 0 
        self.laser_channel = None
        self.running = True

    def switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None):
        self.k.set_Vg(target_vg)
        if laser_cmd1: 
            self.status_update.emit("Configuring laser...")
            self.laser.send_cmd(laser_cmd1, wait_for_reply=False) 
        if laser_cmd2: 
            self.status_update.emit("Toggling laser ON/OFF...")
            self.laser_channel = laser_cmd2["channel"]
            self.laser.send_cmd(laser_cmd2, wait_for_reply=False) 
            self.current_light_state = 1 - self.current_light_state

    def run(self):
        try:
            self.status_update.emit("Initializing Keithley...")
            self.k = Keithley2636B(self.resource_id)
            self.k.connect()
            self.k.clean_instrument()
            self.k.config()

            # Load the power table once for the entire batch
            power_table_path = Path("calibration") / "pp_df.csv"
            if power_table_path.exists():
                power_table = pd.read_csv(power_table_path, index_col=0)
            else:
                self.status_update.emit("Warning: Power table CSV not found!")
                power_table = None

            # --- BATCH PROCESSING LOOP ---
            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                
                self.status_update.emit(f"Loading config: {config_file}...")
                with open(config_file, "r") as f:
                    params = json.load(f)

                # Route files to data folder
                output_dir = Path("data")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                device_num = params['device_number']
                run_num = params['run_number']
                filename = output_dir / f"time_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"time_{device_num}_{run_num}_config.json"
                
                with open(config_backup, "w") as f_back:
                    json.dump(params, f_back, indent=4)

                # Set Keithley params
                self.k.set_nplc('a', params["nplc_a"])
                self.k.set_nplc('b', params["nplc_b"])
                self.k.set_limit('a', params["current_limit_a"])
                self.k.set_limit('b', params["current_limit_b"])
                self.k.set_range('a', params["current_range_a"])
                self.k.set_range('b', params["current_range_b"])
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)
                self.k.set_auto_zero_once() ###
                
                vd_const = float(params["vd_const"])
                self.k.set_Vd(vd_const)
                
                label = params.get("label", f"Run {run_num}")
                self.new_config.emit(config_idx, label)

                # Generate the sequence block dynamically from this config's parameters
                sequence = []
                wavelength_arr = np.array(params.get("wavelength_arr", [450, 532, 660])).astype(int)
                channel_arr = np.array(params.get("channel_arr", [0, 3, 6])).astype(int).astype(str)
                power_arr = np.array(params.get("power_arr"), [100, 100, 100]).astype(int).astype(str)
                
                
                for i in range(len(wavelength_arr)):
                    ch_idx = channel_arr[i]
                    wl = wavelength_arr[i]
                    power = power_arr[i]
                    sequence.extend(single_power_multi_wavelength_basic_block(
                        power_table, ch_idx, wl, power,
                        params["vg_on"], params["vg_off"], 
                        params["duration_1"], params["duration_2"], 
                        params["duration_3"], params["duration_4"]
                    ))
                sequence.extend([{"Vg": params['vg_off'], "duration": params['duration_1']},])
                print(sequence)

                # Start the measurement loop
                start_time = time.time()
                with open(filename, 'w', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"])

                    for step_idx, step in enumerate(sequence):
                        if not self.running: break
                        
                        target_vg = step["Vg"]
                        duration = step["duration"]
                        
                        self.switch_source(target_vg, step.get("laser_cmd1"), step.get("laser_cmd2"))

                        step_end = time.time() + duration
                        self.status_update.emit(f"[{label}] Step {step_idx+1}: Measuring...")
                        
                        last_emit_time = time.time()
                        while time.time() < step_end:
                            if not self.running: break
                            
                            # 1. Catch the raw result in a single variable first
                            reading = self.k.measure()
                            
                            # 2. Make sure it isn't None, AND it actually has 2 items
                            if reading is not None and len(reading) == 2:
                                I_D, I_G = reading # 3. Safe to unpack!
                                
                                if I_D is not None:
                                    t = time.time() - start_time
                                    writer.writerow([t, vd_const, target_vg, I_D, I_G, self.current_light_state])
                                    # self.new_data.emit(config_idx, t, vd_const, target_vg, I_D, I_G)
                                    # 2. THROTTLE the GUI signals to ~20 FPS to prevent freezing!
                                    current_t = time.time()
                                    if current_t - last_emit_time > 0.05:
                                        self.new_data.emit(config_idx, t, vd_const, target_vg, I_D, I_G)
                                        last_emit_time = current_t

                # Clean up after config sweep finishes
                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self.status_update.emit("All Sequences complete. Shutting down hardware...")
            if self.laser and self.current_light_state:
                self.laser.send_cmd({"channel": self.laser_channel, "on": 1}, wait_for_reply=False)
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
        self.setWindowTitle("Batch Time Dependent Transient Response")
        self.worker = worker
        
        # Switched to dictionaries to handle batch plotting
        self.data_memory = {}
        self.lines_id = {}
        self.lines_ig = {}
        self.lines_vd = {}
        self.lines_vg = {}

        self.last_draw_time = time.time()

        self._setup_ui()
        
        self.worker.new_config.connect(self.add_config_line)
        self.worker.new_data.connect(self.update_plot)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.sequence_finished.connect(self.on_finished)
        
        self.worker.start()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.status_label = QLabel("Status: Starting up...")
        self.status_label.setStyleSheet("color: blue; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.figure = Figure(figsize=(10, 7))
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
        if current_time - self.last_draw_time > 0.1:
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

    config_dir = Path("config")
    config_queue = [
        config_dir / "time_dependent_config_1.json",
        config_dir / "time_dependent_config_2.json",
        config_dir / "time_dependent_config_3.json"
    ]

    app = QApplication(sys.argv)
    
    worker = TimeDepWorker(RESOURCE_ID, laser, config_queue)
    window = TimeDepWindow(worker)
    window.show()

    sys.exit(app.exec_())