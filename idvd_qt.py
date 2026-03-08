import sys
import time
import csv
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from keithley.keithley import Keithley2636B
from laser_remote import LaserController

# -------------------------------
# Worker Thread: Automated Id-Vd Sequence
# -------------------------------
class AutoIdVdWorker(QThread):
    new_sweep = pyqtSignal(int, str)  # step_idx, label
    new_data = pyqtSignal(int, float, float, float)  # step_idx, Vd, I_D, I_G
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
                # Note the column header swap: V_G is constant, V_D is swept
                writer.writerow(["Sweep_Label", "V_G", "V_D", "I_D", "I_G"])

                for step_idx, step in enumerate(self.sequence):
                    if not self.running: break

                    label = step["label"]
                    V_G = step["Vg"] # Vg is now the constant
                    vd_points = np.linspace(step["start"], step["stop"], step["points"]) # Vd is swept
                    
                    self.status_update.emit(f"Starting Step {step_idx+1}: {label}")
                    self.new_sweep.emit(step_idx, label) 

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

                    # --- 2. Execute Sweep Setup ---
                    k.enable_output('a', True)
                    k.enable_output('b', True)
                    k.set_autorange('a', 1)
                    k.set_autorange('b', 1)

                    # --- DEPLETION (Using V_G) ---
                    dep_v = step.get("deplete_voltage", None)
                    dep_t = step.get("deplete_time", 5.0) 
                    
                    if dep_v is not None and self.running:
                        self.status_update.emit(f"Depleting Gate at {dep_v}V for {dep_t}s...")
                        k.set_Vd(0.0) # Ensure Vd is 0 during depletion to avoid stress
                        k.set_Vg(dep_v)
                        
                        iterations = int(dep_t / 0.1)
                        for _ in range(iterations): 
                            if not self.running: break
                            time.sleep(0.1)

                    # Apply the constant Gate voltage for the sweep
                    k.set_Vg(V_G)
                    # Move to the start Drain voltage
                    k.set_Vd(step["start"])
                    time.sleep(1) # Initial RC settling

                    # --- 3. Sweep V_D ---
                    self.status_update.emit(f"Sweeping Vd for {label}...")
                    for vd in vd_points:
                        if not self.running: break
                            
                        k.set_Vd(vd)
                        time.sleep(0.1) # Settle delay
                        I_D, I_G = k.measure()
                        
                        if I_D is not None:
                            # Log: Label, Constant Vg, Swept Vd, Id, Ig
                            writer.writerow([label, V_G, vd, I_D, I_G])
                            self.new_data.emit(step_idx, vd, I_D, I_G)

                    # --- 4. Clean up light after step ---
                    if "laser_cmd" in step and laser:
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
# GUI Window
# -------------------------------
class AutoIdVdWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Automated Id-Vd Output Characteristics")
        self.worker = worker
        
        self.lines = {} 
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
        self.ax1.set_title("Automated Steady-State Id-Vd")
        self.ax1.set_ylabel("Drain Current (A)", color='b') # Removed Log label
        self.ax1.set_xlabel("Drain Voltage (V)") # X-axis is now Drain Voltage
        # Linear scale is default, so no set_yscale('log') needed here.
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

    def add_sweep_line(self, step_idx, label):
        """Creates new lines on the plot for Id."""
        # Create the line and assign the label straight from the JSON
        self.lines_id[step_idx], = self.ax1.plot([], [], '.-', markersize=8, label=label)
        
        # Prep the memory dictionaries
        self.data_memory[step_idx] = {"vgs": [], "ids": [], "igs": []}
        
        # Let Matplotlib handle the legend automatically!
        self.ax1.legend(loc='best')
        
        self.canvas.draw()

    def update_plot(self, step_idx, Vd, I_D, I_G):
        self.data_memory[step_idx]["vds"].append(Vd)
        self.data_memory[step_idx]["ids"].append(I_D) # Kept signed to see symmetric behavior
        
        self.lines[step_idx].set_data(
            self.data_memory[step_idx]["vds"], 
            self.data_memory[step_idx]["ids"]
        )
        
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
        self.status_label.setText("Status: Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17" 
    FILENAME = "idvd_auto_sequence.csv"
    num_points = 5

    # --- DEFINE YOUR AUTOPILOT SEQUENCE HERE ---
    # Standard family of output curves (varying Vg)
    sequence = [
        {
            "label": "Vg = -2.0V (Dark)",
            "Vg": -2.0, "start": -2.0, "stop": 2.0, "points": num_points,
            "wait_time": 0,
            "deplete_voltage": -5.0, 
            "deplete_time": 3.0      
        },
        {
            "label": "Vg = 0.0V (Dark)",
            "Vg": 0.0, "start": -2.0, "stop": 2.0, "points": num_points,
            "wait_time": 0,
            "deplete_voltage": -5.0, 
            "deplete_time": 3.0      
        },
        {
            "label": "Vg = 2.0V (Dark)",
            "Vg": 2.0, "start": -2.0, "stop": 2.0, "points": num_points,
            "wait_time": 0,
            "deplete_voltage": -5.0, 
            "deplete_time": 3.0      
        },
        # You can easily add a light sweep to observe photoconductivity in the output curve!
        {
            "label": "Vg = 0.0V (Light 660nm, Pwr 50)",
            "laser_cmd": {"channel": 6, "wavelength": 660, "power": 50},
            "Vg": 0.0, "start": -2.0, "stop": 2.0, "points": num_points,
            "wait_time": 5,
            "deplete_voltage": -5.0, 
            "deplete_time": 3.0      
        }
    ]

    app = QApplication(sys.argv)
    
    worker = AutoIdVdWorker(RESOURCE_ID, LIGHT_IP, FILENAME, sequence)
    window = AutoIdVdWindow(worker)
    window.show()
    
    sys.exit(app.exec_())