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
from LabAuto.laser_remote import LaserController

from pathlib import Path

def get_pp_exact(df, wavelength, power_nw):
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        return None

# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class AutoIdVdWorker(QThread):
    new_sweep = pyqtSignal(int, str)  
    new_data = pyqtSignal(int, float, float, float)  
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.laser = laser 
        self.config_files = config_files_list 
        self.f = None
        self.running = True

    def run(self):
        k = None
        laser = self.laser 
        current_channel = None

        try:
            self.status_update.emit("Initializing Keithley...")
            k = Keithley2636B(self.resource_id)
            k.connect()
            k.clean_instrument()
            k.config()

            for step_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                
                k.set_auto_zero_once()
                
                self.status_update.emit(f"Loading config: {config_file}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                Vg_const = params["vg_const"]
                device_num = params['device_number']
                run_num = params['run_number']
                
                output_dir = Path("data")
                output_dir.mkdir(parents=True, exist_ok=True) 
                    
                filename = output_dir / f"idvd_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"idvd_{device_num}_{run_num}_config.json"
                
                if filename.exists() or config_backup.exists():
                    error_msg = f"FILE EXISTS ERROR: {filename.name} already exists. Stopping experiment."
                    self.status_update.emit(error_msg)
                    self.running = False
                    break  
                
                with open(config_backup, 'w') as f_back:
                    json.dump(params, f_back, indent=4)
                    
                start_time = time.time()
                self.f = open(filename, 'w', newline='')
                writer = csv.writer(self.f)
                # Swapped column order since Vg is const and Vd is swept
                writer.writerow(["V_G", "V_D", "I_D", "I_G"])

                k.set_nplc('a', params["nplc_a"])
                k.set_nplc('b', params["nplc_b"])
                k.set_limit('a', params["current_limit_a"])
                k.set_limit('b', params["current_limit_b"])

                vd_points = np.linspace(params["vd_start"], params["vd_stop"], params["num_points"])
                
                self.status_update.emit(params["label"])
                self.new_sweep.emit(step_idx, params["label"])

                wait_time = params.get("wait_time", 0)
                if wait_time > 0:
                    for i in range(wait_time, 0, -1):
                        if not self.running: break
                        self.status_update.emit(f"Dark Stabilization... {i}s")
                        time.sleep(1)

                dep_v = params.get('deplete_voltage')
                dep_t = int(params.get('deplete_time', 0))
                
                if dep_v is not None and self.running:
                    self.status_update.emit(f"Depleting at {dep_v}V for {dep_t}s...")
                    k.set_Vg(dep_v)
                    if dep_t > 0:
                        for i in range(dep_t, 0, -1):
                            if not self.running: break
                            time.sleep(1)

                if params.get("laser_settings") and laser:
                    laser_settings = params["laser_settings"]
                    power_table = pd.read_csv(Path("calibration") / "pp_df.csv", index_col=0)
                    pp = get_pp_exact(power_table, int(laser_settings['wavelength']), int(laser_settings['power']))
                    cmd = {"channel": laser_settings['channel'], "wavelength": laser_settings['wavelength'], "power": pp}
                    current_channel = cmd["channel"]
                    self.status_update.emit("Configuring Laser")
                    laser.send_cmd(cmd, wait_for_reply=True)
                    
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                    
                    laser_stable_time = int(params.get('laser_stable_time', 0))
                    for i in range(laser_stable_time, 0, -1):
                        if not self.running: break
                        self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                        time.sleep(1)
                
                # --- Execute Sweep ---
                k.set_Vg(Vg_const) # Constant Gate Voltage applied here
                k.enable_output('a', True)
                k.enable_output('b', True)
                k.set_autorange('a', 0)
                k.set_autorange('b', 0)
                
                expected_max_id = params.get("fixed_range_a", 1e-5)
                k.set_range('a', expected_max_id)
                k.set_range('b', 1e-6)  

                base_vd = params.get("base_vd", 0.0)
                pulse_width = params.get("pulse_width", 0.005) 
                rest_time = params.get("rest_time", 0.1)       
                
                # Pre-condition device at resting drain voltage
                k.set_Vd(base_vd)
                time.sleep(1) 

                self.status_update.emit(f"Pulsed Sweeping (Base Vd: {base_vd}V)...")
                
                for vd in vd_points:
                    if not self.running: break
                        
                    # Target VD is pulsed, Base VD is resting state
                    reading = k.measure_pulsed_vd(target_vd=vd, base_vd=base_vd, pulse_width=pulse_width)
                    
                    if reading is not None and len(reading) == 2:
                        I_D, I_G = reading 
                        if I_D is not None:
                            writer.writerow([Vg_const, vd, I_D, I_G])
                            self.new_data.emit(step_idx, vd, I_D, I_G) 
                            
                    time.sleep(rest_time)

                if params.get('laser_settings') and laser and current_channel is not None:
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                    current_channel = None
                    time.sleep(1)
                        
                k.enable_output('a', False)
                k.enable_output('b', False)
                
                if getattr(self, 'f', None) is not None and not self.f.closed:
                    self.f.close()

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
            if getattr(self, 'f', None) is not None and not self.f.closed:
                self.f.close()
            if laser:
                if current_channel is not None:
                    laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=False)
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
class AutoIdVdWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Automated Id-Vd Batch Processor")
        self.worker = worker
        
        self.lines_id = {}
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
        
        # UI Adjusted for Output Characteristics (Vd on X-axis)
        self.ax1.set_title("Automated Pulsed Id-Vd")
        self.ax1.set_xlabel("Drain Voltage (V)")
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

        # Id-Vd curves are typically plotted on a linear Y scale, but keeping log is fine if requested
        self.ax1.set_ylabel("Drain Current |Id| (A)", color='blue')
        self.ax1.tick_params(axis='y', labelcolor='blue')

    def add_sweep_line(self, step_idx, label):
        self.lines_id[step_idx], = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.data_memory[step_idx] = {"vds": [], "ids": []}
        self.ax1.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, step_idx, Vd, I_D, I_G):
        self.data_memory[step_idx]["vds"].append(Vd)
        self.data_memory[step_idx]["ids"].append(abs(I_D))
        
        self.lines_id[step_idx].set_data(self.data_memory[step_idx]["vds"], self.data_memory[step_idx]["ids"])
        
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
        if "FILE EXISTS ERROR" not in self.status_label.text():
            self.status_label.setText("Status: Batch Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "10.0.0.2" 

    print("Connecting to Laser PC...")
    try:
        laser = LaserController(LIGHT_IP)
        print("Laser connected.")
    except Exception:
        laser = None
        print("Running without Laser.")
    
    config_dir = Path("config")
    config_queue = [
        config_dir / 'FORMAL_idvd_pulse_config.json',
    ]
    
    app = QApplication(sys.argv)
    worker = AutoIdVdWorker(RESOURCE_ID, laser, config_queue)
    window = AutoIdVdWindow(worker)
    window.show()
    sys.exit(app.exec_())