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

# def basic_block(power_table, channel_idx, wavelength, target_power, vg_on, vg_off, duration_1, duration_2, duration_3, duration_4):
#     pp = get_pp_exact(power_table, wavelength, target_power)
    
#     basic_block = [
#         {"Vg": vg_off, "duration": duration_1},
#         {"Vg": vg_on, "duration": duration_2, "laser_cmd1": {"channel": channel_idx, "power": pp}},
#         {"Vg": vg_on, "duration": duration_3, "laser_cmd2": {"channel": channel_idx, "on": 1}}, 
#         {"Vg": vg_on, "duration": duration_4, "laser_cmd2": {"channel": channel_idx, "on": 1}}, 
#     ]
#     return basic_block

def basic_block(vg_on, vg_off, duration_1, duration_2):
    
    seqeunce_steps = [
        {"Vg": vg_off, "duration": duration_1},
        {"Vg": vg_on, "duration": duration_2}]
    return seqeunce_steps

# -------------------------------
# Worker Thread: Automated Batch Sequence
# -------------------------------
class TimeDepWorker(QThread):
    new_config = pyqtSignal(int, str) # config_idx, label
    new_data = pyqtSignal(int, float, float, float, float, float) # config_idx, t, Vd, Vg, Id, Ig
    status_update = pyqtSignal(str) # update status string to GUI
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, config_files_list):
        """
        - resource_id: address of Keithley. \n
        - laser: ip of the laser computer (win11). \n
        - config_file_list: list of config files (they are input parameters of measurements). \n
        """
        super().__init__()
        self.resource_id = resource_id
        # self.laser = laser
        # self.servo = servo
        self.config_files = config_files_list
        
        self.k = None
        # self.current_light_state = 0 # 0: dark, 1: light
        # self.servo_state = 0 # 0: blocked, 1: unblocked
        # self.laser_channel = None
        self.running = True

    def switch_source(self, target_vg, laser_cmd1=None, laser_cmd2=None, laser_cmd3=None):
        """
        switch to a specific electric and light source. \n
        - set Vg to target_vg. \n
        - laser_cmd1 = set wavelength or power. \n
        - laser_cmd2 = turn on/off a particular channel. \n
        They are all asynchronous (not wait for reply). \n
        """
        self.k.set_Vg(target_vg)
        if laser_cmd1: 
            self.status_update.emit("Configuring laser...")
            self.laser.send_cmd(laser_cmd1, wait_for_reply=False) 
        if laser_cmd2: 
            self.status_update.emit("Toggling laser ON/OFF...")
            self.laser_channel = laser_cmd2["channel"]
            self.laser.send_cmd(laser_cmd2, wait_for_reply=False) 
            self.current_light_state = 1 - self.current_light_state
        if laser_cmd3:
            self.status_update.emit("Toggling Physical Shutter...")
            if self.servo:
                self.servo.toggle_light() # Calls your toggle logic!
            self.servo_state = 1 - self.servo_state ###

    def run(self):
        try:
            ### set up Keithley
            self.status_update.emit("Initializing Keithley...")
            self.k = Keithley2636B(self.resource_id)
            self.k.connect()
            self.k.clean_instrument()
            self.k.config()

            ### open power table (mapping from power(nW) to pp(%))
            power_table_path = Path("calibration") / "pp_df.csv"
            if power_table_path.exists():
                power_table = pd.read_csv(power_table_path, index_col=0)
            else:
                self.status_update.emit("Warning: Power table CSV not found!")
                power_table = None

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
                
                filename = output_dir / f"time_{device_num}_{run_num}.csv"
                config_backup = output_dir / f"time_{device_num}_{run_num}_config.json"
                
                # Overwrite Protection: if the filename already exists, then stop the measurement
                if filename.exists() or config_backup.exists():
                    error_msg = f"FILE EXISTS ERROR: {filename.name} already exists. Stopping experiment to prevent overwrite!"
                    print(error_msg)
                    self.status_update.emit(error_msg)
                    self.running = False
                    break  # Instantly breaks the config loop and triggers safe shutdown
                
                with open(config_backup, "w") as f_back:
                    json.dump(params, f_back, indent=4)

                # set config parameters from config files
                self.k.set_nplc('a', params["nplc_a"])
                self.k.set_nplc('b', params["nplc_b"])
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
                self.new_config.emit(config_idx, label) #?

                ### build the measurement sequence
                sequence = []
                # for each period, there's a particular channel, wavelength and power
                channel_arr = np.array(params.get("channel_arr", [0, 3, 6])).astype(int).astype(str)
                wavelength_arr = np.array(params.get("wavelength_arr", [450, 532, 660])).astype(int)
                power_arr = np.array(params.get("power_arr", [100, 100, 100])).astype(int).astype(str)

                cycles = int(params["cycle_number"])
                on_off_number = int(params.get("on_off_number", 1))
                print(cycles)
                for c in range(cycles):
                    for i in range(len(wavelength_arr)):
                        ch_idx = channel_arr[i]
                        wl = wavelength_arr[i]
                        power = power_arr[i]
                        unit = basic_block(
                            params["vg_on"], params["vg_off"], 
                            params["duration_1"], params["duration_2"], 
                        )
                        sequence.extend(unit)
                        print(unit)
                    
                unit = [{"Vg": params['vg_off'], "duration": params['duration_1']},]
                sequence.extend(unit)
                print(unit)

                start_time = time.time()
                with open(filename, 'w', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

                    for step_idx, step in enumerate(sequence):
                        if not self.running: break

                        target_vg = step["Vg"]
                        duration = step["duration"]
                        
                        self.switch_source(target_vg)

                        step_end = time.time() + duration
                        self.status_update.emit(f"[{label}] Step {step_idx+1}/{len(sequence)}: Measuring...")
                        
                        last_emit_time = time.time()
                        while time.time() < step_end:
                            if not self.running: break
                            
                            reading = self.k.measure()
                            # proceed if it's a successful measurement
                            if reading is not None and len(reading) == 2:
                                I_D, I_G = reading 
                                
                                if I_D is not None:
                                    t = time.time() - start_time
                                     # always update data to csv file
                                    writer.writerow([t, vd_const, target_vg, I_D, I_G])

                                    # not update the figure too frequently (there are lots of points)
                                    current_t = time.time()
                                    if current_t - last_emit_time > 0.2:
                                        self.new_data.emit(config_idx, t, vd_const, target_vg, I_D, I_G)
                                        last_emit_time = current_t

                self.k.enable_output('a', False)
                self.k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")
            
        finally:
            self.status_update.emit("All Sequences complete. Shutting down hardware...")

            # if self.servo and self.servo.is_on:
            #     self.status_update.emit("Closing physical shutter...")
            #     self.servo.toggle_light() # Force it back to the OFF angle

            # if self.laser:
            #     # stop the measurement -> turn off the light
            #     if self.current_light_state and self.laser_channel is not None:
            #         self.laser.send_cmd({"channel": self.laser_channel, "on": 1}, wait_for_reply=False)
            #     # Cleanly close the laser network socket
            #     self.laser.close() 
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

    # print("Connecting to Laser PC...")
    # laser = LaserController(LASER_IP)
    # print("Laser connected.")

    # print("Connecting to Servo Shutter...")
    # try:
        # servo = ServoController() # Your class that handles the auto-port connection
        # print("Servo connected.")
    # except Exception as e:
    #     print(f"Warning: Could not connect to servo ({e}). Running without physical shutter.")
    #     servo = None

    config_dir = Path("config")
    config_queue = [
        config_dir / "time_dependent_config_app.json",
        # config_dir / "time_dependent_config_2.json",
        # config_dir / "time_dependent_config_3.json"
    ]

    app = QApplication(sys.argv)
    
    worker = TimeDepWorker(RESOURCE_ID, config_queue)
    window = TimeDepWindow(worker)
    window.show()

    sys.exit(app.exec_())