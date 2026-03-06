import sys
import time
import csv
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from keithley.keithley import Keithley2636B
from LabAuto.network import Connection

class LaserController:
    def __init__(self, laser_ip, port=5001):
        self.conn = Connection.connect(laser_ip, port)

    def send_cmd(self, payload, wait_for_reply=True):
        self.conn.send_json(payload)
        if wait_for_reply:
            return self.conn.receive_json()

    def close(self):
        self.conn.close()

# -------------------------------
# Worker Thread: Handles Hardware
# -------------------------------
class TimeDepWorker(QThread):
    # This signal safely transports data to the GUI without locking it
    new_data = pyqtSignal(float, float, float, float, float) # t, Vd, Vg, Id, Ig
    status_update = pyqtSignal(str)
    sequence_finished = pyqtSignal()

    def __init__(self, resource_id, laser_ip, laser_channel, sequence, filename, Vd_const=1.0):
        super().__init__()
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.laser_channel = laser_channel
        self.sequence = sequence
        self.filename = filename
        self.Vd_const = Vd_const
        self.running = True

    def run(self):
        k = None
        laser = None
        current_light_state = 0
        
        try:
            self.status_update.emit("Connecting to Keithley...")
            k = Keithley2636B(self.resource_id)
            k.connect()
            k.clean_instrument()
            k.config()
            k.set_nplc('a', "1.0")
            k.set_nplc('b', "1.0")
            k.enable_output('a', True)
            k.enable_output('b', True)
            k.set_Vd(self.Vd_const)

            self.status_update.emit(f"Connecting to Light PC ({self.laser_ip})...")
            laser = LaserController(self.laser_ip)
            
            start_time = time.time()

            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G", "Light_State"])

                for step_idx, step in enumerate(self.sequence):
                    if not self.running: break
                    
                    target_vg = step["Vg"]
                    duration = step["duration"]
                    k.set_Vg(target_vg)
                    
                    self.status_update.emit(f"Step {step_idx+1}: Vg={target_vg}V, Light={'Changing' if 'laser_cmd1' in step else 'Hold'}")

                    # --- Synchronous GUI Click Setup ---
                    if "laser_cmd1" in step:
                        self.status_update.emit("Waiting for Light PC GUI to configure...")
                        laser.send_cmd(step["laser_cmd1"], wait_for_reply=True) 

                    # --- Instant Laser Toggle ---
                    if "laser_cmd2" in step:
                        self.status_update.emit("Triggering Light!")
                        laser.send_cmd(step["laser_cmd2"], wait_for_reply=False) 
                        current_light_state = 1 - current_light_state

                    # --- Measuring Loop ---
                    step_end = time.time() + duration
                    self.status_update.emit(f"Step {step_idx+1}: Measuring...")
                    
                    while time.time() < step_end:
                        if not self.running: break
                        
                        I_D, I_G = k.measure()
                        if I_D is not None:
                            t = time.time() - start_time
                            
                            # Save to CSV
                            writer.writerow([t, self.Vd_const, target_vg, I_D, I_G, current_light_state])
                            
                            # Safely send data to GUI using PyQt Signal
                            self.new_data.emit(t, self.Vd_const, target_vg, I_D, I_G)

        except Exception as e:
            print(f"Hardware Error: {e}")
            
        finally:
            self.status_update.emit("Shutting down hardware...")
            if laser:
                # Guarantee light is off
                laser.send_cmd({"channel": self.laser_channel, "on": 1}, wait_for_reply=False)
                laser.close()
            if k:
                k.shutdown()
                
            self.sequence_finished.emit()

    def stop(self):
        self.running = False
        self.wait()


# -------------------------------
# Main GUI Window
# -------------------------------
class TimeDepWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.setWindowTitle("Time Dependent Transient Response")
        self.worker = worker
        
        # Memory allocation for plot
        self.times, self.I_Ds, self.I_Gs, self.V_Ds, self.V_Gs = [], [], [], [], []

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Setup Matplotlib Canvas
        self.figure = Figure(figsize=(10, 7))
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

        self.line_id, = self.ax1.plot([], [], 'b.-', label='Id')
        self.line_ig, = self.ax2.plot([], [], 'r.-', label='Ig')
        self.line_vd, = self.ax1_v.plot([], [], 'g.-', alpha=0.3)
        self.line_vg, = self.ax2_v.plot([], [], 'k.-', alpha=0.3)

        # Connect the worker signals to GUI slots
        self.worker.new_data.connect(self.update_plot)
        self.worker.status_update.connect(lambda msg: print(f"GUI STATUS: {msg}"))
        self.worker.sequence_finished.connect(self.on_finished)
        
        # Start the background thread automatically
        self.worker.start()

    def update_plot(self, t, Vd, Vg, I_D, I_G):
        """This function only runs in the main thread when a signal arrives!"""
        self.times.append(t)
        self.V_Ds.append(Vd)
        self.V_Gs.append(Vg)
        self.I_Ds.append(I_D)
        self.I_Gs.append(I_G)
        
        self.line_id.set_data(self.times, self.I_Ds)
        self.line_ig.set_data(self.times, self.I_Gs)
        self.line_vd.set_data(self.times, self.V_Ds)
        self.line_vg.set_data(self.times, self.V_Gs)
        
        for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
            ax.relim()
            ax.autoscale_view()
            
        self.canvas.draw()

    def on_finished(self):
        print("Experiment complete. Hardware is safe.")

    def closeEvent(self, event):
        """Ensures safe shutdown if you click the 'X' button mid-measurement"""
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LASER_IP = "192.168.50.17"
    LASER_CHANNEL = 6
    FILENAME = "time_dep_laser_pyqt.csv"

    sequence = [
        {"Vg": -1.5, "duration": 3},
        {"Vg": 0.5, "duration": 3, 
         "laser_cmd1": {"channel": 6, "power": 50, "wavelength": 532}}, 
        {"Vg": 0.5, "duration": 5, 
         "laser_cmd2": {"channel": 6}}, 
        {"Vg": 0.5, "duration": 3, 
         "laser_cmd2": {"channel": 6}}, 
    ]

    app = QApplication(sys.argv)
    
    # Pass the hardware details to the background worker
    worker = TimeDepWorker(RESOURCE_ID, LASER_IP, LASER_CHANNEL, sequence, FILENAME)
    
    # Hand the worker to the GUI window
    window = TimeDepWindow(worker)
    window.show()
    
    sys.exit(app.exec_())