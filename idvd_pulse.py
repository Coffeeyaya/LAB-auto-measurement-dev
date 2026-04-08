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

def get_pp_exact(df, wavelength, power_nw):
    try:
        return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError:
        return None

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

        self.k = None
        self.power_table = None
        self.running = True
        self.current_channel = None 

        self.expected_max_id = None
        self.expected_max_ig = None
    
    def _init_hardware(self):
        self.status_update.emit("Initializing Keithley...")
        self.k = Keithley2636B(self.resource_id)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()

        pt_path = Path("calibration") / "pp_df.csv"
        if pt_path.exists():
            self.power_table = pd.read_csv(pt_path, index_col=0)
        else:
            self.status_update.emit("Warning: Power table CSV not found!")
    
    def _setup_files(self, params):
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True) 

        device_num = params['device_number']
        run_num = params['run_number']
            
        filename = output_dir / f"idvd_{device_num}_{run_num}.csv"
        config_backup = output_dir / f"idvd_{device_num}_{run_num}_config.json"
        
        if filename.exists() or config_backup.exists():
            raise FileExistsError(f"{filename.name} already exists. Aborting to prevent overwrite!")
        
        with open(config_backup, 'w') as f_back:
            json.dump(params, f_back, indent=4)

        return filename
    
    def _apply_keithley_settings(self, params):
        self.k.set_auto_zero_once()
        self.k.set_nplc('a', params["nplc_a"])
        self.k.set_nplc('b', params["nplc_b"])
        self.k.set_limit('a', params["current_limit_a"])
        self.k.set_limit('b', params["current_limit_b"])
        
        # Disable Autorange for pulses
        self.k.set_autorange('a', 0)
        self.k.set_autorange('b', 0)
        
        # Set FIXED ranges
        self.expected_max_id = params.get("fixed_range_a", 1e-5)
        self.expected_max_ig = params.get("fixed_range_b", 1e-6)
        self.k.set_range('a', self.expected_max_id)
        self.k.set_range('b', self.expected_max_ig)

    def _precondition_device(self, params):
        wait_time = params.get("wait_time", 0)
        if wait_time > 0:
            for i in range(wait_time, 0, -1):
                if not self.running: break
                self.status_update.emit(f"Dark Stabilization... {i}s")
                time.sleep(1)

        dep_v = params.get('deplete_voltage')
        dep_t = int(params.get('deplete_time', 0))
        
        if dep_v is not None and self.running:
            self.status_update.emit(f"Depleting Gate at {dep_v}V for {dep_t}s...")
            self.k.set_Vd(0.0) 
            self.k.set_Vg(dep_v)
            if dep_t > 0:
                for i in range(dep_t, 0, -1):
                    if not self.running: break
                    time.sleep(1)

    def _setup_laser(self, params):
        if params.get("laser_settings") and self.laser:
            laser_settings = params["laser_settings"]
            pp = get_pp_exact(self.power_table, int(laser_settings['wavelength']), int(laser_settings['power']))
            
            cmd = {"channel": laser_settings['channel'], "wavelength": laser_settings['wavelength'], "power": pp}
            self.current_channel = cmd["channel"]
            
            self.status_update.emit("Configuring Laser")
            self.laser.send_cmd(cmd, wait_for_reply=True)
            self.status_update.emit("Turning Light ON...")
            self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
            
            laser_stable_time = int(params.get('laser_stable_time', 0))
            for i in range(laser_stable_time, 0, -1):
                if not self.running: break
                self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                time.sleep(1)

    def _execute_measurement(self, filename, params, config_idx, label):
        vg_const = float(params["vg_const"])
        base_vd = params.get("base_vd", 0.0)
        base_vg = params.get("base_vg", 0.0)
        pulse_width = params.get("pulse_width", 0.005)
        rest_time = params.get("rest_time", 0.1)     
        
        self.k.set_Vd(base_vd)
        time.sleep(1) 

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["V_G", "V_D", "I_D", "I_G"])

            self.status_update.emit(f"[{label}] Pulsed Sweeping (Base Vd: {base_vd}V)...")
            vd_points = np.linspace(params["vd_start"], params["vd_stop"], params["num_points"])

            for vd in vd_points:
                if not self.running: break
                    
                reading = self.k.measure_pulsed_vd_vg(target_vd=vd, target_vg=vg_const, base_vd=base_vd, base_vg=base_vg, pulse_width=pulse_width)
                
                if reading is not None and len(reading) == 2:
                    I_D, I_G = reading 
                    if I_D is not None:
                        # Two-way clamp: Prevents Keithley Overflows!
                        I_D_record = max(-self.expected_max_id, min(self.expected_max_id, I_D))
                        I_G_record = max(-self.expected_max_ig, min(self.expected_max_ig, I_G))

                        writer.writerow([vg_const, vd, I_D_record, I_G_record])
                        self.new_data.emit(config_idx, vd, I_D_record, I_G_record) 
                        
                time.sleep(rest_time)

    def run(self):
        try:
            self._init_hardware()

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                
                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)

                try:
                    filename = self._setup_files(params)
                except FileExistsError as e:
                    self.status_update.emit(f"ERROR: {e}")
                    break 

                self._apply_keithley_settings(params)
                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_sweep.emit(config_idx, label)

                self._precondition_device(params)
                self._setup_laser(params)

                self.k.enable_output('a', True)
                self.k.enable_output('b', True)

                self._execute_measurement(filename, params, config_idx, label)

                if params.get('laser_settings') and self.laser and self.current_channel is not None:
                    self.status_update.emit(f"Sweep done. Turning OFF Laser Ch {self.current_channel}...")
                    self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
                    self.current_channel = None
                    time.sleep(1)

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
            if self.laser:
                if self.current_channel is not None:
                    self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=False)
                self.laser.close()
            if self.k:
                self.k.shutdown()
                
            if "FILE EXISTS ERROR" not in getattr(self, 'status_label_text', ""): 
                for config_file in self.config_files:
                    try:
                        config_file.unlink() 
                    except Exception:
                        pass

            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

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
        self.worker.status_update.connect(self.update_status)
        self.worker.sequence_finished.connect(self.on_finished)
        self.worker.start()

    def update_status(self, text):
        self.status_label.setText(text)
        self.worker.status_label_text = text

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
        self.ax1.set_title("Automated Pulsed Id-Vd")
        self.ax1.set_xlabel("Drain Voltage (V)")
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)
        self.ax1.set_ylabel("Drain Current Id (A)", color='blue')
        self.ax1.tick_params(axis='y', labelcolor='blue')

    def add_sweep_line(self, step_idx, label):
        self.lines_id[step_idx], = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.data_memory[step_idx] = {"vds": [], "ids": [], "igs": []}
        self.ax1.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, step_idx, Vd, I_D, I_G):
        self.data_memory[step_idx]["vds"].append(Vd)
        self.data_memory[step_idx]["ids"].append(I_D)
        self.data_memory[step_idx]["igs"].append(I_G) 
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
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "10.0.0.2" 
    
    queue_dir = Path("config/idvd_queue")
    if not queue_dir.exists():
        print(f"Queue directory {queue_dir} not found!")
        sys.exit()

    config_queue = sorted(list(queue_dir.glob("*.json")))
    if not config_queue:
        print("Queue is empty. Exiting.")
        sys.exit()

    needs_laser = False
    for config_path in config_queue:
        try:
            with open(config_path, "r") as f:
                params = json.load(f)
                if params.get("laser_settings") is not None:
                    needs_laser = True
                    break 
        except Exception:
            pass

    if needs_laser:
        print("Laser required by config. Connecting to Laser PC...")
        try:
            laser = LaserController(LIGHT_IP)
            print("Laser connected.")
        except Exception as e:
            print(f"Connection failed ({e}). Running without laser.")
            laser = None
    else:
        print("No laser needed for this batch. Bypassing connection.")
        laser = None
    
    app = QApplication(sys.argv)
    worker = AutoIdVdWorker(RESOURCE_ID, laser, config_queue)
    window = AutoIdVdWindow(worker)
    window.show()
    sys.exit(app.exec_())