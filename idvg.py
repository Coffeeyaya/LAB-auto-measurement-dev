import sys
import time
import csv
import os
import json
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from keithley.keithley import Keithley2636B
from laser_remote import LaserController

from pathlib import Path

def get_pp_exact(df, wavelength, power_nw):
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        return None
# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class AutoIdVgWorker(QThread):
    new_sweep = pyqtSignal(int, str)  
    new_data = pyqtSignal(int, float, float, float)  
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    # --- MODIFIED: Accept 'laser' directly instead of 'laser_ip' ---
    def __init__(self, resource_id, laser, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.laser = laser 
        self.config_files = config_files_list 
        self.f = None
        self.running = True

    def run(self):
        k = None
        # --- MODIFIED: Use the laser object passed from __main__ ---
        laser = self.laser 
        current_channel = None

        try:
            self.status_update.emit("Initializing Keithley...")
            k = Keithley2636B(self.resource_id)
            k.connect()
            k.clean_instrument()
            k.config()

            # --- MODIFIED: Removed the internal connection step here ---

            # --- BATCH PROCESSING LOOP ---
            for step_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                self.k.set_auto_zero_once() ###
                
                self.status_update.emit(f"Loading config: {config_file}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                Vd_const = params["vd_const"]
                device_num = params['device_number']
                run_num = params['run_number']
                
                output_dir = Path("data")
                output_dir.mkdir(parents=True, exist_ok=True) 
                    
                filename = output_dir / f"idvg_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"idvg_{device_num}_{run_num}_config.json"
                
                with open(config_backup, 'w') as f_back:
                    json.dump(params, f_back, indent=4)
                start_time = time.time()
                self.f = open(filename, 'w', newline='')
                writer = csv.writer(self.f)
                writer.writerow(["V_D", "V_G", "I_D", "I_G"])

                k.set_nplc('a', params["nplc_a"])
                k.set_nplc('b', params["nplc_b"])
                k.set_limit('a', params["current_limit_a"])
                k.set_limit('b', params["current_limit_b"])

                vg_points = np.linspace(params["vg_start"], params["vg_stop"], params["num_points"])
                
                self.status_update.emit(params["label"])
                self.new_sweep.emit(step_idx, params["label"])

                wait_time = int(params['wait_time'])
                if wait_time > 0:
                    for i in range(wait_time, 0, -1):
                        if not self.running: break
                        self.status_update.emit(f"Dark Stabilization... {i}s")
                        time.sleep(1)

                # --- DEPLETION ---
                dep_v = params.get('deplete_voltage')
                dep_t = int(params.get('deplete_time', 0))
                
                if dep_v is not None and self.running:
                    self.status_update.emit(f"Depleting at {dep_v}V for {dep_t}s...")
                    k.set_Vg(dep_v)
                    
                    if dep_t > 0:
                        for i in range(dep_t, 0, -1):
                            if not self.running: break
                            self.status_update.emit(f"Depleting at {dep_v}V for {i}s")
                            time.sleep(1)

                # --- Prepare Light (if specified) ---
                if params.get("laser_settings") and laser:
                    laser_settings = params["laser_settings"]
                    table = pd.read_csv(Path("calibration") / "pp_df.csv", index_col=0)
                    pp = get_pp_exact(table, int(laser_settings['wavelength']), int(laser_settings['power']))
                    cmd = {"channel": laser_settings['channel'], "wavelength": laser_settings['wavelength'], "power": pp}
                    current_channel = cmd["channel"]
                    self.status_update.emit("Configuring Laser")
                    laser.send_cmd(cmd, wait_for_reply=True)
                    
                    self.status_update.emit("Turning Light ON...")
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                    
                    laser_stable_time = int(params.get('laser_stable_time', 0))
                    for i in range(laser_stable_time, 0, -1):
                        if not self.running: break
                        self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                        time.sleep(1)
                
                # --- Execute Sweep ---
                k.set_Vd(Vd_const)
                k.enable_output('a', True)
                k.enable_output('b', True)
                k.set_autorange('a', 1)
                k.set_autorange('b', 1)    

                k.set_Vg(params["vg_start"])
                time.sleep(1) 

                self.status_update.emit("Sweeping ...")
                for vg in vg_points:
                    if not self.running: break
                        
                    k.set_Vg(vg)
                    time.sleep(0.1) 
                    # 1. Catch the raw result in a single variable first
                    reading = k.measure()
                    
                    # 2. Make sure it isn't None, AND it actually has 2 items
                    if reading is not None and len(reading) == 2:
                        I_D, I_G = reading # 3. Safe to unpack!
                        
                        if I_D is not None:
                            writer.writerow([Vd_const, vg, I_D, I_G])
                            self.new_data.emit(step_idx, vg, I_D, I_G) # FIXED

                # --- Clean up step ---
                # NOTE: Ensure params.get() here matches the key used earlier! ('laser_settings' vs 'laser_cmd')
                if params.get('laser_settings') and laser and current_channel is not None:
                    self.status_update.emit(f"Sweep done. Turning OFF Laser Ch {current_channel}...")
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                    current_channel = None
                    time.sleep(1)
                        
                k.enable_output('a', False)
                k.enable_output('b', False)
                
                if hasattr(self, 'f') and not self.f.closed:
                    self.f.close()

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
            if hasattr(self, 'f') and not self.f.closed:
                self.f.close()
            if laser:
                if current_channel is not None:
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=False)
                # The worker can still safely call .close() here before exiting
                laser.close()
            if k:
                k.shutdown()
                
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

# -------------------------------
# GUI Window (Monitor Only)
# -------------------------------
class AutoIdVgWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Automated Id-Vg Batch Processor")
        self.worker = worker
        
        self.lines_id = {}
        self.lines_ig = {}
        self.data_memory = {}
        
        self.last_draw_time = time.time()

        self._setup_ui()
        
        self.worker.new_sweep.connect(self.add_sweep_line)
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

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.ax1 = self.figure.add_subplot(111)
        
        self.ax1.set_title("Automated Steady-State Id-Vg")
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

        self.ax1.set_ylabel("Drain Current |Id| (A)", color='blue')
        self.ax1.set_yscale('log')
        self.ax1.tick_params(axis='y', labelcolor='blue')

    def add_sweep_line(self, step_idx, label):
        self.lines_id[step_idx], = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.data_memory[step_idx] = {"vgs": [], "ids": [], "igs": []}
        self.ax1.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, step_idx, Vg, I_D, I_G):
        self.data_memory[step_idx]["vgs"].append(Vg)
        self.data_memory[step_idx]["ids"].append(abs(I_D))
        self.data_memory[step_idx]["igs"].append(abs(I_G)) 
        
        self.lines_id[step_idx].set_data(self.data_memory[step_idx]["vgs"], self.data_memory[step_idx]["ids"])
        
        current_time = time.time()
        if current_time - self.last_draw_time > 0.1:
            if self.ax1.get_autoscale_on():
                self.ax1.relim()
                self.ax1.autoscale_view()
                
            self.canvas.draw()
            self.last_draw_time = current_time

    def on_finished(self):
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()
            
        self.canvas.draw()
        self.status_label.setText("Status: Batch Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17" 

    # --- MODIFIED: Establish connection before launching GUI ---
    print("Connecting to Laser PC...")
    laser = LaserController(LIGHT_IP)
    print("Laser connected.")
    
    config_dir = Path("config")
    config_queue = [
        config_dir / 'idvg_config_1.json',
        config_dir / 'idvg_config_2.json',
        config_dir / 'idvg_config_3.json'
    ]
    
    app = QApplication(sys.argv)
    
    # --- MODIFIED: Pass the 'laser' object to the worker ---
    worker = AutoIdVgWorker(RESOURCE_ID, laser, config_queue)
    window = AutoIdVgWindow(worker)
    window.show()
    
    sys.exit(app.exec_())