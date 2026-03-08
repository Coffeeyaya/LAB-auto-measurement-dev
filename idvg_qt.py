import sys
import time
import csv
import os
import json
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from keithley.keithley import Keithley2636B
from laser_remote import LaserController

# -------------------------------
# Worker Thread: Automated Sequence
# -------------------------------
class AutoIdVgWorker(QThread):
    # Signals to safely talk to the GUI
    new_sweep = pyqtSignal(str)  # label (tells GUI to make a new line)
    new_data = pyqtSignal(float, float, float)  # Vg, I_D, I_G
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser_ip, filename, idvg_config_file):
        super().__init__()
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.filename = filename
        self.f = None
        self.running = True
        with open(idvg_config_file, "r") as f:
            self.parameters = json.load(f)
        self.Vd_const = self.parameters["vd_const"]

    def run(self):
        k = None
        laser = None
        current_channel = None

        try:
            self.status_update.emit("Initializing Keithley...")
            k = Keithley2636B(self.resource_id)
            k.connect()
            k.clean_instrument()
            k.config()
            # overwrite settings in k.config()
            k.set_nplc('a', self.parameters["nplc_a"])
            k.set_nplc('b', self.parameters["nplc_b"])
            k.set_limit('a', self.parameters["current_limit_a"])
            k.set_limit('b', self.parameters["current_limit_b"])

            if self.laser_ip:
                self.status_update.emit(f"Connecting to Light PC ({self.laser_ip})...")
                laser = LaserController(self.laser_ip)

            self.f = open(self.filename, 'w', newline='')
            writer = csv.writer(self.f)
            writer.writerow(["V_D", "V_G", "I_D", "I_G"])

            vg_points = np.linspace(self.parameters["vg_start"], self.parameters["vg_stop"], self.parameters["num_points"])
            
            self.status_update.emit(self.parameters["label"])
            self.new_sweep.emit(self.parameters["label"])

            wait_time = int(self.parameters['wait_time'])
            if wait_time > 0:
                for i in range(wait_time, 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Dark Stabilization... {i}s")
                    time.sleep(1)

            # --- DEPLETION ---
            dep_v = self.parameters['deplete_voltage']
            dep_t = int(self.parameters['deplete_time'])
            
            if dep_v is not None and self.running:
                self.status_update.emit(f"Depleting at {dep_v}V for {dep_t}s...")
                k.set_Vg(dep_v)
                
                if dep_t > 0:
                    for i in range(dep_t, 0, -1):
                        if not self.running: break
                        self.status_update.emit(f"Depleting at {dep_v} for {i}s")
                        time.sleep(1)

            # --- 1. Prepare Light (if specified) ---
            if self.parameters["laser_cmd"] and laser:
                cmd = self.parameters["laser_cmd"]
                current_channel = cmd["channel"]
                self.status_update.emit(f"Configuring Laser")
                laser.send_cmd(cmd, wait_for_reply=True)
                
                self.status_update.emit("Turning Light ON...")
                laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                
                laser_stable_time = int(self.parameters['laser_stable_time'])
                for i in range(laser_stable_time, 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                    time.sleep(1)
            
            # --- 2. Execute Sweep ---
            k.set_Vd(self.Vd_const)

            k.enable_output('a', True)
            k.enable_output('b', True)
            k.set_autorange('a', 1)
            k.set_autorange('b', 1)    

            # Move to the actual start voltage of the sweep
            k.set_Vg(self.parameters["vg_start"])

            time.sleep(1) # Initial RC settling

            self.status_update.emit(f"Sweeping ...")
            for vg in vg_points:
                if not self.running: break
                    
                k.set_Vg(vg)
                time.sleep(0.1) # Settle delay
                I_D, I_G = k.measure()
                
                if I_D is not None:
                    writer.writerow([self.Vd_const, vg, I_D, I_G])
                    self.new_data.emit(vg, I_D, I_G)

            # --- 3. Clean up light after step ---
            if self.parameters['laser_cmd'] and laser:
                self.status_update.emit(f"Sweep done. Turning OFF Laser Ch {current_channel}...")
                laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                current_channel = None
                time.sleep(1)
                    
            k.enable_output('a', False)
            k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
            if hasattr(self, 'f') and not self.f.closed:
                self.f.close()
            if laser:
                if current_channel is not None:
                    # Failsafe: Ensure it's off
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
class AutoIdVgWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Automated Id-Vg Transfer Characteristics")
        self.worker = worker
        
        self.vgs = []
        self.ids = []
        self.igs = []
        
        self.last_draw_time = time.time()

        self._setup_ui()
        
        # Connect signals
        self.worker.new_sweep.connect(self.add_sweep_line)
        self.worker.new_data.connect(self.update_plot)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.sequence_finished.connect(self.on_finished)
        
        # START AUTOMATICALLY
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
        
        # --- TWIN AXIS SETUP ---
        self.ax1 = self.figure.add_subplot(111)
        self.ax2 = self.ax1.twinx() # Create the right-side axis sharing the same X-axis
        
        self.ax1.set_title("Automated Steady-State Id-Vg")
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

        # Left Axis (Id) - Blue
        self.ax1.set_ylabel("Drain Current |Id| (A)", color='blue')
        self.ax1.set_yscale('log')
        self.ax1.tick_params(axis='y', labelcolor='blue')

        # Right Axis (Ig) - Red
        self.ax2.set_ylabel("Gate Current |Ig| (A)", color='red')
        self.ax2.set_yscale('log')
        self.ax2.tick_params(axis='y', labelcolor='red')

    def add_sweep_line(self, label):
        """Creates new lines on the plot for Id and Ig on separate axes."""
        # Plot Id on ax1 (Left), Ig on ax2 (Right)
        self.line_id, = self.ax1.plot([], [], 'b.-', markersize=8, label=f"Id ({label})")
        self.line_ig, = self.ax2.plot([], [], 'r.-', markersize=8, label=f"Ig ({label})")
        
        # Combine the legends from both axes into a single box
        lines = [self.line_id, self.line_ig]
        labels = [l.get_label() for l in lines]
        self.ax1.legend(lines, labels, loc='best')
        
        self.canvas.draw()

    def update_plot(self, Vg, I_D, I_G):
        """Appends data and updates the plot smoothly."""
        self.vgs.append(Vg)
        self.ids.append(abs(I_D))
        self.igs.append(abs(I_G)) 
        
        self.line_id.set_data(self.vgs, self.ids)
        self.line_ig.set_data(self.vgs, self.igs)
        
        # Frame-rate throttle
        current_time = time.time()
        if current_time - self.last_draw_time > 0.1:
            # Must rescale BOTH axes independently!
            if self.ax1.get_autoscale_on():
                self.ax1.relim()
                self.ax1.autoscale_view()
            if self.ax2.get_autoscale_on():
                self.ax2.relim()
                self.ax2.autoscale_view()
                
            self.canvas.draw()
            self.last_draw_time = current_time

    def on_finished(self):
        # Final redraw for both axes
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()
        if self.ax2.get_autoscale_on():
            self.ax2.relim()
            self.ax2.autoscale_view()
            
        self.canvas.draw()
        self.status_label.setText("Status: Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17" 
    idvg_config_file = 'idvg_config.json'
    with open(idvg_config_file, 'r') as f:
        parameters = json.load(f)
    device_number = parameters['device_number']
    run_number = parameters['run_number']
    FILENAME = f"idvg_{device_number}_{run_number}.csv"

    app = QApplication(sys.argv)
    
    # Worker is much cleaner now!
    worker = AutoIdVgWorker(RESOURCE_ID, LIGHT_IP, FILENAME, idvg_config_file)
    
    window = AutoIdVgWindow(worker)
    window.show()
    
    sys.exit(app.exec_())