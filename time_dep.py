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

# ==========================================
# THE UNIVERSAL STEADY-STATE WORKER THREAD
# ==========================================
class UniversalSteadyWorker(QThread):
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
        self.power_table = None
        self.running = True

        self.current_light_state = 0 
        self.servo_state = 0 
        self.laser_channel = None
        self.current_applied_vg = None

    # ------------------------------------------
    # SETUP HELPERS
    # ------------------------------------------
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
        
        device = params.get('device_number', '0')
        run_num = params.get('run_number', 1)
        
        filename = output_dir / f"time_steady_{device}_{run_num}.csv"
        config_backup = output_dir / f"time_steady_{device}_{run_num}_config.json"
        
        if filename.exists() or config_backup.exists():
            raise FileExistsError(f"{filename.name} already exists. Aborting to prevent overwrite!")
            
        with open(config_backup, "w") as f_back:
            json.dump(params, f_back, indent=4)
            
        return filename
    
    def _apply_keithley_settings(self, params):
        self.k.set_auto_zero_once()
        self.k.set_nplc('a', params["nplc_a"])
        self.k.set_nplc('b', params["nplc_b"])
        self.k.set_limit('a', params["current_limit_a"])
        self.k.set_limit('b', params["current_limit_b"])
        
        # For steady state, autorange is perfectly fine and often preferred.
        self.k.set_autorange('a', 1)
        self.k.set_autorange('b', 1)
        
        # Give it a starting point based on UI settings
        if "current_range_a" in params:
            self.k.set_range('a', params["current_range_a"])
        if "current_range_b" in params:
            self.k.set_range('b', params["current_range_b"])

    # ------------------------------------------
    # THE UNIVERSAL SEQUENCE BUILDER
    # ------------------------------------------
    def _build_master_sequence(self, params):
        """Intelligently builds the timeline based on the requested hardware mode."""
        sequence = []
        hardware_mode = params.get("hardware_mode", "Dark Current")
        
        vg_off = params.get('vg_off', 0.0)
        vg_on = params.get('vg_on', 1.0)
        cycle_number = int(params.get("cycle_number", 1))

        # --- MODE 1: DARK CURRENT ---
        if hardware_mode == "Dark Current":
            for _ in range(cycle_number):
                sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 5.0)})
                sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
            sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 5.0)}) # Final Relax
            return sequence

        # --- OPTICAL MODES SETUP ---
        channels = np.array(params.get("channel_arr", [0])).astype(int).astype(str)
        wavelengths = np.array(params.get("wavelength_arr", [660])).astype(int)
        powers = np.array(params.get("power_arr", [100])).astype(int).astype(str)
        
        ch_idx = channels[0]
        pp = get_pp_exact(self.power_table, wavelengths[0], powers[0])

        # Optical Preamble
        sequence = [
            {"Vg": vg_off, "duration": 5.0, "laser_cmd1": {"channel": ch_idx, "power": pp}},
            {"Vg": vg_off, "duration": 3.0, "laser_cmd2": {"channel": ch_idx, "on": 1}},
        ]

        # --- MODE 2: LASER ONLY ---
        if hardware_mode == "Laser Only":
            for _ in range(cycle_number):
                for i in range(len(wavelengths)):
                    sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 5.0)})
                    sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
                    for _ in range(int(params.get("on_off_number", 1))):
                        sequence.append({"Vg": vg_on, "duration": params.get("duration_3", 2.0), "laser_cmd2": {"channel": ch_idx, "on": 1}})
                        sequence.append({"Vg": vg_on, "duration": params.get("duration_4", 2.0), "laser_cmd2": {"channel": ch_idx, "on": 1}})
        
        # --- MODE 3: LASER + SERVO ---
        elif hardware_mode == "Laser + Servo":
            for _ in range(cycle_number):
                for i in range(len(wavelengths)):
                    sequence.append({"Vg": vg_off, "duration": params.get("duration_1", 5.0)})
                    sequence.append({"Vg": vg_on,  "duration": params.get("duration_2", 1.0)})
                    for _ in range(int(params.get("on_off_number", 1))):
                        sequence.append({"Vg": vg_on, "duration": params.get("servo_time_on", 1.0), "laser_cmd3": 1})
                        sequence.append({"Vg": vg_on, "duration": params.get("servo_time_off", 1.0), "laser_cmd3": 1})

        # Optical Postamble
        sequence.append({"Vg": vg_off, "duration": 5.0, "laser_cmd2": {"channel": ch_idx, "on": 1}})
        return sequence

    # ------------------------------------------
    # EXECUTION HELPERS
    # ------------------------------------------
    def _switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None):
        # In Continuous DC Mode, we actively change the physical Gate Voltage here
        if target_vg != self.current_applied_vg:
            self.k.set_Vg(target_vg)
            self.current_applied_vg = target_vg

        if laser_cmd1 and self.laser: 
            self.status_update.emit("Configuring laser...")
            self.laser.send_cmd(laser_cmd1, wait_for_reply=False) 
        if laser_cmd2 and self.laser: 
            self.status_update.emit("Toggling laser ON/OFF...")
            self.laser_channel = laser_cmd2["channel"]
            self.laser.send_cmd(laser_cmd2, wait_for_reply=False) 
            self.current_light_state = 1 - self.current_light_state
        if laser_cmd3 and self.servo:
            self.status_update.emit("Toggling Physical Shutter...")
            self.servo.toggle_light()
            self.servo_state = 1 - self.servo_state 

    def _execute_measurement(self, filename, params, sequence, config_idx, label):
        vd_const = float(params["vd_const"])
        start_time = time.time()
        last_emit_time = start_time

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State", "Servo_State"])

            for step_idx, step in enumerate(sequence):
                if not self.running: break

                target_vg = step["Vg"]
                self._switch_source(target_vg, step.get("laser_cmd1"), step.get("laser_cmd2"), step.get("laser_cmd3"))
                
                step_end = time.time() + step["duration"]
                self.status_update.emit(f"[{label}] Step {step_idx+1}/{len(sequence)}: Continuous Read at {target_vg}V...")
                
                # --- CONTINUOUS HIGH-SPEED SAMPLING LOOP ---
                while time.time() < step_end:
                    if not self.running: break

                    reading = self.k.measure()
                    
                    if reading and len(reading) == 2:
                        I_D, I_G = reading 
                        if I_D is not None:
                            t = time.time() - start_time
                            writer.writerow([t, vd_const, target_vg, I_D, I_G, self.current_light_state, self.servo_state])

                            current_t = time.time()
                            if current_t - last_emit_time > 0.2:
                                self.new_data.emit(config_idx, t, vd_const, target_vg, I_D, I_G)
                                last_emit_time = current_t

    def _shutdown_hardware(self):
        self.status_update.emit("Shutting down hardware safely...")
        if self.servo and getattr(self.servo, 'is_on', False):
            self.servo.toggle_light() 
        if self.laser:
            if self.current_light_state and self.laser_channel is not None:
                self.laser.send_cmd({"channel": self.laser_channel, "on": 1}, wait_for_reply=False)
            self.laser.close() 
        if self.k:
            self.k.shutdown()

    # ------------------------------------------
    # ORCHESTRATOR
    # ------------------------------------------
    def run(self):
        try:
            self._init_hardware()

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break

                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                for i in range(params.get("wait_time", 0), 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Initial wait... {i}s")
                    time.sleep(1)

                try:
                    filename = self._setup_files(params)
                except FileExistsError as e:
                    self.status_update.emit(f"ERROR: {e}")
                    break 

                self._apply_keithley_settings(params)
                self.k.set_Vd(float(params["vd_const"]))
                self.k.enable_output('a', True)
                self.k.enable_output('b', True)

                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_config.emit(config_idx, label)
                
                sequence = self._build_master_sequence(params)
                self._execute_measurement(filename, params, sequence, config_idx, label)

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self._shutdown_hardware()
            
            if "FILE EXISTS ERROR" not in getattr(self, 'status_label_text', ""): 
                self.status_update.emit("Clearing Queue Files...")
                for config_file in self.config_files:
                    try:
                        config_file.unlink() 
                    except Exception as e:
                        print(f"Could not delete {config_file}: {e}")

            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

# ==========================================
# GUI WINDOW
# ==========================================
class TimeDepWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Universal Steady-State Time-Dependent Measurement")
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
        self.ax2_v.set_ylabel("Vg Applied (V)", color='black')

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
    LASER_IP = "10.0.0.2"

    # ==========================================
    # 1. READ QUEUE
    # ==========================================
    queue_dir = Path("config/timedep_queue")
    if not queue_dir.exists():
        print(f"Queue directory {queue_dir} not found!")
        sys.exit()

    config_queue = sorted(list(queue_dir.glob("*.json")))
    if not config_queue:
        print("Queue is empty. Exiting.")
        sys.exit()

    # ==========================================
    # 2. PRE-SCAN CONFIGS FOR HARDWARE NEEDS
    # ==========================================
    needs_laser = False
    needs_servo = False
    
    for config_path in config_queue:
        try:
            with open(config_path, "r") as f:
                params = json.load(f)
                hw_mode = params.get("hardware_mode", "Dark Current")
                
                if hw_mode in ["Laser Only", "Laser + Servo"]:
                    needs_laser = True
                if hw_mode == "Laser + Servo":
                    needs_servo = True
        except Exception as e:
            print(f"Warning: Could not pre-read {config_path.name} - {e}")

    # ==========================================
    # 3. CONDITIONALLY CONNECT TO HARDWARE
    # ==========================================
    laser = None
    servo = None
    
    if needs_laser:
        print("Laser required by config. Connecting to Laser PC...")
        try:
            laser = LaserController(LASER_IP)
            print("✅ Laser connected.")
        except Exception as e:
            print(f"❌ Laser Connection failed ({e}). Running without laser.")

    if needs_servo:
        print("Servo required by config. Connecting to Shutter...")
        try:
            servo = ServoController() 
            print("✅ Servo connected.")
        except Exception as e:
            print(f"❌ Servo Connection failed ({e}). Running without physical shutter.")
            
    if not needs_laser and not needs_servo:
        print("✅ Standard Dark Current required. Bypassing optical connections.")

    # ==========================================
    # 4. LAUNCH APP
    # ==========================================
    app = QApplication(sys.argv)
    worker = UniversalSteadyWorker(RESOURCE_ID, laser, servo, config_queue)
    window = TimeDepWindow(worker)
    window.show()
    sys.exit(app.exec_())