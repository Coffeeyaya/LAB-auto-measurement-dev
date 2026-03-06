import sys
import time
import csv
import os
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
    new_sweep = pyqtSignal(int, str)  # step_idx, label (tells GUI to make a new line)
    new_data = pyqtSignal(int, float, float, float)  # step_idx, Vg, I_D, I_G
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser_ip, filename, sequence):
        super().__init__()
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.filename = filename
        self.sequence = sequence
        self.running = True

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
            k.keithley.write("smua.measure.nplc = 8.0")
            k.keithley.write("smub.measure.nplc = 8.0")

            if self.laser_ip:
                self.status_update.emit(f"Connecting to Light PC ({self.laser_ip})...")
                laser = LaserController(self.laser_ip)

            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Sweep_Label", "V_D", "V_G", "I_D", "I_G"])

                # Iterate through the automated sequence
                for step_idx, step in enumerate(self.sequence):
                    if not self.running: break

                    label = step["label"]
                    V_D = step["Vd"]
                    vg_points = np.linspace(step["start"], step["stop"], step["points"])
                    
                    self.status_update.emit(f"Starting Step {step_idx+1}: {label}")
                    self.new_sweep.emit(step_idx, label) # Tell GUI to prep a new line

                    # --- 1. Prepare Light (if specified) ---
                    if "laser_cmd" in step and laser:
                        cmd = step["laser_cmd"]
                        current_channel = cmd["channel"]
                        
                        self.status_update.emit(f"Configuring Laser (Ch:{cmd['channel']}, Wl:{cmd['wavelength']}, Pwr:{cmd['power']})...")
                        laser.send_cmd(cmd, wait_for_reply=True)
                        
                        self.status_update.emit("Turning Light ON...")
                        laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                        
                        wait_time = step.get("wait_time", 3)
                        for i in range(wait_time, 0, -1):
                            if not self.running: break
                            self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                            time.sleep(1)
                    else:
                        wait_time = step.get("wait_time", 0)
                        if wait_time > 0:
                            for i in range(wait_time, 0, -1):
                                if not self.running: break
                                self.status_update.emit(f"Dark Stabilization... {i}s")
                                time.sleep(1)

                    # --- 2. Execute Sweep ---
                    k.set_Vd(V_D)
                    k.set_Vg(step["start"])
                    k.enable_output('a', True)
                    k.enable_output('b', True)
                    k.set_autorange('a', 1)
                    k.set_autorange('b', 1)
                    time.sleep(1) # Initial RC settling

                    self.status_update.emit(f"Sweeping {label}...")
                    for vg in vg_points:
                        if not self.running: break
                            
                        k.set_Vg(vg)
                        time.sleep(0.1) # Settle delay
                        I_D, I_G = k.measure()
                        
                        if I_D is not None:
                            writer.writerow([label, V_D, vg, I_D, I_G])
                            self.new_data.emit(step_idx, vg, I_D, I_G)

                    # --- 3. Clean up light after step ---
                    if "laser_cmd" in step and laser:
                        self.status_update.emit(f"Sweep done. Turning OFF Laser Ch {current_channel}...")
                        laser.send_cmd({"channel": current_channel, "on": 1}, wait_for_reply=True)
                        time.sleep(1)
                        
                    k.enable_output('a', False)
                    k.enable_output('b', False)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Sequence complete. Shutting down hardware...")
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
        
        self.lines = {} # Stores Matplotlib lines by step_idx
        self.data_memory = {} # Stores Vgs, IDs by step_idx
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
        
        self.ax1 = self.figure.add_subplot(111)
        self.ax1.set_title("Automated Steady-State Id-Vg")
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

    def add_sweep_line(self, step_idx, label):
        """Creates a new line on the plot for the current sequence step."""
        line, = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.lines[step_idx] = line
        self.data_memory[step_idx] = {"vgs": [], "ids": []}
        self.ax1.legend()
        self.canvas.draw()

    def update_plot(self, step_idx, Vg, I_D, I_G):
        """Appends data to the correct line and updates the plot smoothly."""
        self.data_memory[step_idx]["vgs"].append(Vg)
        self.data_memory[step_idx]["ids"].append(abs(I_D))
        
        self.lines[step_idx].set_data(
            self.data_memory[step_idx]["vgs"], 
            self.data_memory[step_idx]["ids"]
        )
        
        # Frame-rate throttle
        current_time = time.time()
        if current_time - self.last_draw_time > 0.1:
            if self.ax1.get_autoscale_on():
                self.ax1.relim()
                self.ax1.autoscale_view()
            self.canvas.draw()
            self.last_draw_time = current_time

    def on_finished(self):
        # Final redraw
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()
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
    FILENAME = "idvg_auto_sequence.csv"
    num_points = 3
    # --- DEFINE YOUR AUTOPILOT SEQUENCE HERE ---
    sequence = [
        {
            "label": "Dark Sweep",
            "Vd": 1.0, "start": -3.0, "stop": 3.0, "points": num_points,
            "wait_time": 0
        },
        {
            "label": "Light Sweep (660nm, Pwr 10)",
            "laser_cmd": {"channel": 6, "wavelength": 660, "power": 10},
            "Vd": 1.0, "start": -3.0, "stop": 3.0, "points": num_points,
            "wait_time": 5
        },
        {
            "label": "Light Sweep (660nm, Pwr 50)",
            "laser_cmd": {"channel": 6, "wavelength": 660, "power": 50},
            "Vd": 1.0, "start": -3.0, "stop": 3.0, "points": num_points,
            "wait_time": 5
        }
    ]

    app = QApplication(sys.argv)
    
    worker = AutoIdVgWorker(RESOURCE_ID, LIGHT_IP, FILENAME, sequence)
    window = AutoIdVgWindow(worker)
    window.show()
    
    sys.exit(app.exec_())