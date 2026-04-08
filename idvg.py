import sys
import time
import csv
import json
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from keithley.keithley import Keithley2636B
from LabAuto.laser_remote import LaserController
from pathlib import Path

def get_pp_exact(df, wavelength, power_nw):
    try: return float(df.loc[int(wavelength), str(power_nw)])
    except KeyError: return None

class AutoIdVgWorker(QThread):
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

    def _init_hardware(self):
        self.status_update.emit("Initializing Keithley...")
        self.k = Keithley2636B(self.resource_id)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()
        pt_path = Path("calibration") / "pp_df.csv"
        if pt_path.exists(): self.power_table = pd.read_csv(pt_path, index_col=0)

    def _setup_files(self, params):
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True) 
        filename = output_dir / f"idvg_{params['device_number']}_{params['run_number']}.csv"
        config_backup = output_dir / f"idvg_{params['device_number']}_{params['run_number']}_config.json"
        if filename.exists() or config_backup.exists(): raise FileExistsError(f"{filename.name} exists. Aborting.")
        with open(config_backup, 'w') as f: json.dump(params, f, indent=4)
        return filename
    
    def _apply_keithley_settings(self, params):
        self.k.set_auto_zero_once()
        self.k.set_nplc('a', params["nplc_a"])
        self.k.set_nplc('b', params["nplc_b"])
        self.k.set_limit('a', params["current_limit_a"])
        self.k.set_limit('b', params["current_limit_b"])
        self.k.set_autorange('a', 1)
        self.k.set_autorange('b', 1)

    def _precondition_device(self, params):
        wait_time = params.get("wait_time", 0)
        for i in range(wait_time, 0, -1):
            if not self.running: break
            self.status_update.emit(f"Dark Stabilization... {i}s")
            time.sleep(1)
        dep_v = params.get('deplete_voltage')
        dep_t = int(params.get('deplete_time', 0))
        if dep_v is not None and self.running:
            self.status_update.emit(f"Depleting at {dep_v}V for {dep_t}s...")
            self.k.set_Vg(dep_v)
            for i in range(dep_t, 0, -1):
                if not self.running: break
                time.sleep(1)

    def _setup_laser(self, params):
        if params.get("laser_settings") and self.laser:
            ls = params["laser_settings"]
            pp = get_pp_exact(self.power_table, ls['wavelength'], ls['power'])
            self.current_channel = ls["channel"]
            self.status_update.emit("Configuring Laser")
            self.laser.send_cmd({"channel": ls['channel'], "wavelength": ls['wavelength'], "power": pp}, wait_for_reply=True)
            self.status_update.emit("Turning Light ON...")
            self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
            for i in range(int(params.get('laser_stable_time', 0)), 0, -1):
                if not self.running: break
                self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                time.sleep(1)

    def _execute_measurement(self, filename, params, config_idx, label):
        vd_const = float(params["vd_const"])
        self.k.set_Vg(params["vg_start"])
        time.sleep(1) 

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["V_D", "V_G", "I_D", "I_G"])

            self.status_update.emit(f"[{label}] Steady Sweeping...")
            vg_points = np.linspace(params["vg_start"], params["vg_stop"], params["num_points"])
            delay = params.get("source_to_measure_delay", 0.01)

            for vg in vg_points:
                if not self.running: break
                self.k.set_Vg(vg)
                time.sleep(delay) 
                reading = self.k.measure()
                if reading and len(reading) == 2:
                    I_D, I_G = reading 
                    if I_D is not None:
                        writer.writerow([vd_const, vg, I_D, I_G])
                        self.new_data.emit(config_idx, vg, I_D, I_G) 

    def run(self):
        try:
            self._init_hardware()
            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f: params = json.load(f)
                try: filename = self._setup_files(params)
                except FileExistsError as e:
                    self.status_update.emit(f"ERROR: {e}")
                    break 

                self._apply_keithley_settings(params)
                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_sweep.emit(config_idx, label)

                self._precondition_device(params)
                self._setup_laser(params)
                
                self.k.set_Vd(float(params["vd_const"]))
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)

                self._execute_measurement(filename, params, config_idx, label)

                if params.get('laser_settings') and self.laser and self.current_channel is not None:
                    self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
                    self.current_channel = None
                    time.sleep(1)

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e: self.status_update.emit(f"Error: {e}")
        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
            if self.laser:
                if self.current_channel is not None: self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=False)
                self.laser.close()
            if self.k: self.k.shutdown()
            
            if "FILE EXISTS ERROR" not in getattr(self, 'status_label_text', ""):
                for f in self.config_files: f.unlink()
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

class AutoIdVgWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Automated Id-Vg Batch Processor")
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
        if "FILE EXISTS ERROR" not in self.status_label.text():
            self.status_label.setText("Status: Batch Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        if self.worker.isRunning(): self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "10.0.0.2" 
    
    queue_dir = Path("config/idvg_queue")
    if not queue_dir.exists(): sys.exit()
    config_queue = sorted(list(queue_dir.glob("*.json")))
    if not config_queue: sys.exit()

    needs_laser = False
    for config_path in config_queue:
        try:
            with open(config_path, "r") as f:
                if json.load(f).get("laser_settings") is not None:
                    needs_laser = True
                    break 
        except: pass

    if needs_laser:
        try: laser = LaserController(LIGHT_IP)
        except: laser = None
    else: laser = None
    
    app = QApplication(sys.argv)
    worker = AutoIdVgWorker(RESOURCE_ID, laser, config_queue)
    window = AutoIdVgWindow(worker)
    window.show()
    sys.exit(app.exec_())