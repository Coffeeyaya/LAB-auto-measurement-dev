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

# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class TimeDepWorker(QThread):
    new_config = pyqtSignal(int, str) # config_idx, label
    new_data = pyqtSignal(int, float, float, float, float) # config_idx, t, Vd, Vg, Id (Removed Ig for clean plotting if needed, but keeping data format)
    status_update = pyqtSignal(str) # update status string to GUI
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.config_files = config_files_list
        self.k = None
        self.running = True

    def run(self):
        try:
            ### set up Keithley
            self.status_update.emit("Initializing Keithley...")
            self.k = Keithley2636B(self.resource_id)
            self.k.connect()
            self.k.clean_instrument()
            self.k.config()

            ### process measurement based on config files
            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break

                # before each measurement, auto zero once
                self.k.set_auto_zero_once()
                
                # open config file for input parameters
                self.status_update.emit(f"Loading config: {config_file}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                # wait time before measure
                wait_time = params.get("wait_time", 0)
                for i in range(wait_time, 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Wait ... {i}s")
                    time.sleep(1)

                # data folder for storing data and backup config files
                output_dir = Path("data")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                device_num = params.get('device_number', '0')
                run_num = int(params.get('run_number', 1))
                
                filename = output_dir / f"time_dark_pulse_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"time_dark_pulse_{device_num}_{run_num}_config.json"
                
                # Overwrite Protection
                if filename.exists() or config_backup.exists():
                    error_msg = f"FILE EXISTS ERROR: {filename.name} already exists. Stopping experiment to prevent overwrite!"
                    print(error_msg)
                    self.status_update.emit(error_msg)
                    self.running = False
                    break 
                
                with open(config_backup, "w") as f_back:
                    json.dump(params, f_back, indent=4)

                # set config parameters from config files
                self.k.set_nplc('a', params.get("nplc_a", 0.1)) # Fast NPLC for pulsing!
                self.k.set_nplc('b', params.get("nplc_b", 0.1))
                self.k.set_limit('a', params["current_limit_a"])
                self.k.set_limit('b', params["current_limit_b"])
                self.k.set_range('a', params["current_range_a"])
                self.k.set_range('b', params["current_range_b"])
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)
                
                # set constant Vd
                vd_const = float(params["vd_const"])
                self.k.set_Vd(vd_const)
                
                label = params.get("label", f"Run {run_num}")
                self.new_config.emit(config_idx, label)

                ### build the PURE DARK measurement sequence
                sequence = []
                cycles = int(params.get("cycle_number", 1))
                
                # Simply alternate between Vg_off and Vg_on based on their durations
                for c in range(cycles):
                    sequence.append({"Vg": params["vg_off"], "duration": params["duration_1"]})
                    sequence.append({"Vg": params["vg_on"],  "duration": params["duration_2"]})
                    
                # Return to resting state at the end
                sequence.append({"Vg": params['vg_off'], "duration": params['duration_1']})

                start_time = time.time()
                with open(filename, 'w', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    # Simplified CSV Header for dark current
                    writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

                    for step_idx, step in enumerate(sequence):
                        if not self.running: break

                        target_vg = step["Vg"]
                        step_end = time.time() + step["duration"]
                        self.status_update.emit(f"[{label}] Cycle Step {step_idx+1}/{len(sequence)}: Measuring {target_vg}V...")
                        
                        # --- PULL VARIABLES OUTSIDE THE LOOP ---
                        base_vg = float(params.get("base_vg", 0.0))
                        pulse_width = float(params.get("pulse_width_ms", 5.0)) / 1000.0
                        
                        pulse_fired = False 
                        last_emit_time = time.time()
                        
                        # --- THE ONLY WHILE LOOP WE NEED ---
                        while time.time() < step_end:
                            if not self.running: break

                            # Sleep for the remaining fraction of a second at the very end
                            time_left = step_end - time.time()
                            if time_left < 0.01:
                                time.sleep(max(0, time_left))
                                break

                            # --- THE SINGLE-PULSE RELAXATION ENGINE ---
                            if not pulse_fired:
                                # 1. Fire the single excitation pulse at the very beginning
                                reading = self.k.measure_pulsed_vg(target_vg, base_vg, pulse_width)
                                print(f"DEBUG: Pulse fired. Target: {target_vg}V, Width: {pulse_width}s. Reading = {reading}")
                                pulse_fired = True
                                recorded_vg = target_vg # Record the spike in the CSV
                            else:
                                # 2. Continuous Relaxation Tracking
                                # Instantly sample the current at the resting voltage
                                reading = self.k.measure_pulsed_vg(base_vg, base_vg, 0.01)
                                recorded_vg = base_vg   # Record the resting voltage in the CSV
                            # ------------------------------------------

                            # Proceed if it's a successful measurement
                            if reading is not None and len(reading) == 2:
                                I_D, I_G = reading
                                
                                if I_D is not None:
                                    t = time.time() - start_time
                                    
                                    writer.writerow([t, vd_const, recorded_vg, I_D, I_G])

                                    current_t = time.time()
                                    if current_t - last_emit_time > 0.2:
                                        self.new_data.emit(config_idx, t, vd_const, recorded_vg, I_D, I_G)
                                        last_emit_time = current_t

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self.status_update.emit("All Sequences complete. Shutting down hardware...")
            if self.k:
                self.k.shutdown()
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

# -------------------------------
# GUI Window (Unchanged)
# -------------------------------
class TimeDepWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Dark Current Pulse Measurement")
        self.worker = worker
        
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
        
        if "FILE EXISTS ERROR" not in self.status_label.text():
            self.status_label.setText("Batch Sequence Finished. Hardware is safe.")

    def closeEvent(self, event): 
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

    config_dir = Path("config")
    # You can still use the same JSON, the script will just ignore the optical parameters
    config_queue = [
        config_dir / "FORMAL_time_dependent_config_pulse_app.json",
    ]

    app = QApplication(sys.argv)
    
    # We no longer pass the laser or servo into the worker!
    worker = TimeDepWorker(RESOURCE_ID, config_queue)
    window = TimeDepWindow(worker)
    window.show()

    sys.exit(app.exec_())