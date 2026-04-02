import sys
import time
import csv
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from keithley.keithley import Keithley2636B

# ==========================================
# EXTERNAL HELPER FUNCTIONS
# ==========================================
def build_dark_block(params):
    """Generates a single measurement cycle: Relaxation -> Pulse."""
    vg_on = params["vg_on"]
    vg_off = params["vg_off"]
    
    # Using 'duration_off' and 'duration_on' for clarity, 
    # but falling back to duration_1 / duration_2 if using your old JSONs
    dur_off = params.get("duration_off", params.get("duration_1", 5.0))
    dur_on = params.get("duration_on", params.get("duration_2", 1.0))
    
    sequence = [
        {"Vg": vg_off, "duration": dur_off}, # 1. Dark relaxation
        {"Vg": vg_on,  "duration": dur_on}   # 2. Vg Excitation Pulse
    ]
    return sequence

# ==========================================
# THE MODULAR WORKER THREAD
# ==========================================
class DarkPulseWorker(QThread):
    new_config = pyqtSignal(int, str)
    new_data = pyqtSignal(int, float, float, float, float, float)
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, config_files_list):
        super().__init__()
        self.resource_id = resource_id
        self.config_files = config_files_list
        
        self.k = None
        self.running = True
        self.current_applied_vg = None

    # ------------------------------------------
    # 1. SETUP HELPERS
    # ------------------------------------------
    def _init_hardware(self):
        """Connects to and resets the Keithley."""
        self.status_update.emit("Initializing Keithley...")
        self.k = Keithley2636B(self.resource_id)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()

    def _setup_files(self, params):
        """Creates the data directory and handles Overwrite Protection."""
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        device = params.get('device_number', '0')
        run_num = int(params.get('run_number', 1))
        
        filename = output_dir / f"time_dark_{device}_{run_num}.csv"
        config_backup = output_dir / f"time_dark_{device}_{run_num}_config.json"
        
        if filename.exists() or config_backup.exists():
            raise FileExistsError(f"{filename.name} already exists. Aborting to prevent overwrite!")
            
        with open(config_backup, "w") as f_back:
            json.dump(params, f_back, indent=4)
            
        return filename

    def _apply_keithley_settings(self, params):
        """Applies NPLC, Limits, Ranges, and the baseline Drain Voltage."""
        self.k.set_auto_zero_once()
        self.k.set_nplc('a', params.get("nplc_a", 1.0))
        self.k.set_nplc('b', params.get("nplc_b", 1.0))
        self.k.set_limit('a', params.get("current_limit_a", 1e-3))
        self.k.set_limit('b', params.get("current_limit_b", 1e-3))
        self.k.set_range('a', params.get("current_range_a", 1e-4))
        self.k.set_range('b', params.get("current_range_b", 1e-4))
        
        self.k.set_Vd(float(params["vd_const"]))
        self.k.enable_output('a', True)
        self.k.enable_output('b', True)

    def _build_master_sequence(self, params):
        """Loops through cycles to build the full run."""
        sequence = []
        for _ in range(int(params.get("cycle_number", 1))):
            unit = build_dark_block(params)
            sequence.extend(unit)
                
        # Final dark relaxation step to watch the current decay
        final_dur = params.get("duration_off", params.get("duration_1", 5.0))
        sequence.append({"Vg": params['vg_off'], "duration": final_dur})
        return sequence

    # ------------------------------------------
    # 2. EXECUTION HELPERS
    # ------------------------------------------
    def _apply_vg(self, target_vg):
        """Updates the physical hardware Gate Voltage asynchronously."""
        # Update Gate Voltage only if changed (saves USB bandwidth)
        if target_vg != self.current_applied_vg:
            self.k.set_Vg(target_vg)
            self.current_applied_vg = target_vg

    def _execute_measurement(self, filename, params, sequence, config_idx, label):
        """The tight sampling loop that talks to the Keithley and logs data."""
        vd_const = float(params["vd_const"])
        start_time = time.time()
        last_emit_time = start_time

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            # Removed Light_State and Servo_State
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

            for step_idx, step in enumerate(sequence):
                if not self.running: break

                # Trigger Hardware Changes
                self._apply_vg(step["Vg"])

                step_end = time.time() + step["duration"]
                self.status_update.emit(f"[{label}] Step {step_idx+1}/{len(sequence)}: Measuring...")
                
                # The high-speed continuous sampling loop
                while time.time() < step_end:
                    if not self.running: break

                    # Sleep remaining milliseconds to keep timing mathematically exact
                    time_left = step_end - time.time()
                    if time_left < 0.01:
                        time.sleep(max(0, time_left))
                        break

                    reading = self.k.measure()
                    
                    if reading and len(reading) == 2:
                        I_D, I_G = reading 
                        if I_D is not None:
                            t = time.time() - start_time
                            
                            # Log every point to CSV
                            writer.writerow([t, vd_const, step["Vg"], I_D, I_G])

                            # Update GUI at 5Hz (every 0.2s) to prevent crashes
                            current_t = time.time()
                            if current_t - last_emit_time > 0.2:
                                self.new_data.emit(config_idx, t, vd_const, step["Vg"], I_D, I_G)
                                last_emit_time = current_t

    def _shutdown_hardware(self):
        """Safely powers down the Keithley."""
        self.status_update.emit("Shutting down Keithley safely...")
        if self.k:
            self.k.shutdown()

    # ------------------------------------------
    # 3. THE MAIN ORCHESTRATOR
    # ------------------------------------------
    def run(self):
        """The Master Loop."""
        try:
            self._init_hardware()

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break

                # 1. Load Parameters
                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)
                
                # 2. Wait Timer (if requested)
                for i in range(params.get("wait_time", 0), 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Initial wait... {i}s")
                    time.sleep(1)

                # 3. Setup Files (Catches Overwrite Errors instantly)
                try:
                    filename = self._setup_files(params)
                except FileExistsError as e:
                    self.status_update.emit(f"ERROR: {e}")
                    break 

                # 4. Prepare Hardware & Sequence
                self._apply_keithley_settings(params)
                label = params.get("label", f"Run {params.get('run_number', 1)}")
                self.new_config.emit(config_idx, label)
                
                sequence = self._build_master_sequence(params)

                # 5. Execute the Physics Measurement
                self._execute_measurement(filename, params, sequence, config_idx, label)

                # Turn off Keithley outputs between runs
                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self._shutdown_hardware()
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()

# ==========================================
# GUI WINDOW
# ==========================================
class DarkPulseWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Dark Vg Pulse Measurement")
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

# ==========================================
# EXECUTION ENTRY
# ==========================================
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

    config_dir = Path("config")
    config_queue = [
        config_dir / "FORMAL_time_dependent_config.json"
    ]

    app = QApplication(sys.argv)
    
    worker = DarkPulseWorker(RESOURCE_ID, config_queue)
    window = DarkPulseWindow(worker)
    window.show()

    sys.exit(app.exec_())