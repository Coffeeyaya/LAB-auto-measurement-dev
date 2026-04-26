import sys
import json
import csv
import time
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal

from LabAuto.laser_remote import LaserController
from base_worker import BaseMeasurementWorker, SweepData
from base_gui import BaseMeasurementWindow

class AutoIdVgWorker(BaseMeasurementWorker):
    new_sweep = pyqtSignal(int, str)  
    new_data = pyqtSignal(int, object) # Emits the SweepData dataclass

    def run(self):
        """Orchestrates the tools for a steady-state measurement."""
        try:
            self._init_hardware()
            self._get_power_table()

            for config_idx, config_file in enumerate(self.config_files):
                if not self.running: break
                
                self.status_update.emit(f"Loading config: {config_file.name}...")
                with open(config_file, "r") as f:
                    params = json.load(f)

                try:
                    filename = self._setup_files(params, prefix="idvg")
                except FileExistsError as e:
                    self.status_label_text = f"FILE EXISTS ERROR: {e}"
                    self.status_update.emit(self.status_label_text)
                    break 

                self._apply_base_keithley_settings(params, autorange=True)
                self._precondition_device(params)
                self._setup_laser_steady(params)
                
                # Hand off to the specific measurement loop
                self._execute_idvg_measurement(filename, params, config_idx)

                # Step Cleanup
                if params.get('laser_settings') and self.laser and self.current_channel is not None:
                    self.laser.send_cmd({"channel": self.current_channel, "on": 1}, wait_for_reply=True)
                    self.current_channel = None

        except Exception as e:
            self.status_update.emit(f"Hardware Error: {e}")
            
        finally:
            self._shutdown_hardware()
            self._cleanup_queue()
            self.sequence_finished.emit()

    def _execute_idvg_measurement(self, filename, params, config_idx):
        """The specific Id-Vg physics loop."""
        label = params.get("label", f"Run {params.get('run_number', 1)}")
        self.new_sweep.emit(config_idx, label)
        
        vd_const = float(params["vd_const"])
        self.k.set_Vd(vd_const)
        self.k.set_Vg(params["vg_start"])
        
        self.k.enable_output('a', True)
        self.k.enable_output('b', True)
        time.sleep(1) 

        self.status_update.emit(f"[{label}] Steady Sweeping Vd={vd_const}V...")
        # 1. Generate the forward sweep
        vg_start = float(params["vg_start"])
        vg_stop = float(params["vg_stop"])
        num_points = int(params["num_points"])
        
        vg_points_forward = np.linspace(vg_start, vg_stop, num_points)
        
        # 2. Check the JSON config for Dual Sweep
        if params.get("sweep_direction") == "Dual Sweep (Forward + Reverse)":
            # Generate reverse sweep, but slice off the first point [1:] 
            # so we don't measure the peak voltage twice in a row!
            vg_points_reverse = np.linspace(vg_stop, vg_start, num_points)[1:]
            
            # Glue them together into one seamless array
            vg_points = np.concatenate((vg_points_forward, vg_points_reverse))
            self.status_update.emit(f"[{label}] Dual Sweeping Vd={vd_const}V...")
        else:
            vg_points = vg_points_forward
            self.status_update.emit(f"[{label}] Forward Sweeping Vd={vd_const}V...")
        delay = params.get("source_to_measure_delay", 0.01)

        with open(filename, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["V_D", "V_G", "I_D", "I_G"])

            for vg in vg_points:
                if not self.running: break
                
                # self.k.set_Vg(vg)
                # time.sleep(delay)
                reading = self.k.measure_vg(vg, source_to_measure_delay=delay)
                
                if reading and len(reading) == 2:
                    I_D, I_G = reading 
                    if I_D is not None:
                        I_D_clamped, I_G_clamped = self.clamp_data(I_D, I_G)
                        writer.writerow([vd_const, vg, I_D_clamped, I_G_clamped])
                        packet = SweepData(Vd=vd_const, Vg=vg, Id=I_D_clamped, Ig=I_G_clamped)
                        self.new_data.emit(config_idx, packet) 

        self.k.enable_output('a', False)
        self.k.enable_output('b', False)


class AutoIdVgWindow(BaseMeasurementWindow):
    def __init__(self, worker):
        super().__init__(worker, window_title="Steady Id-Vg")
        
        self.worker.new_sweep.connect(self.add_sweep_line)
        self.worker.new_data.connect(self.update_plot)

    def _setup_custom_axes(self):
        self.ax1 = self.figure.add_subplot(111)
        self.ax1.set_title("Automated Steady-State Id-Vg")
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_ylabel("Drain Current |Id| (A)", color='blue')
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

    def add_sweep_line(self, step_idx, label):
        self.lines_dict[step_idx], = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.data_memory[step_idx] = {"vgs": [], "ids": []}
        self.ax1.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, step_idx, data: SweepData):
        # Extract the data cleanly using dot-notation
        self.data_memory[step_idx]["vgs"].append(data.Vg)
        self.data_memory[step_idx]["ids"].append(abs(data.Id))
        
        self.lines_dict[step_idx].set_data(
            self.data_memory[step_idx]["vgs"], 
            self.data_memory[step_idx]["ids"]
        )
        
        current_time = time.time()
        if current_time - self.last_draw_time > 0.1:
            if self.ax1.get_autoscale_on():
                self.ax1.relim()
                self.ax1.autoscale_view()
            self.canvas.draw()
            self.last_draw_time = current_time


if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "10.0.0.2" 
    
    queue_dir = Path("config/idvg_queue")
    if not queue_dir.exists():
        print(f"Queue directory {queue_dir} not found!")
        sys.exit()

    config_queue = sorted(list(queue_dir.glob("*.json")))
    if not config_queue:
        print("Queue is empty. Exiting.")
        sys.exit()

    needs_laser = any("laser_settings" in json.load(open(f)) for f in config_queue)
    laser = None

    if needs_laser:
        print("Laser required by config. Connecting to Laser PC...")
        try:
            laser = LaserController(LIGHT_IP)
            print("Laser connected.")
        except Exception as e:
            print(f"Connection failed ({e}). Running without laser.")
    
    app = QApplication(sys.argv)
    worker = AutoIdVgWorker(RESOURCE_ID, config_queue, laser=laser)
    window = AutoIdVgWindow(worker)
    window.show()
    sys.exit(app.exec_())