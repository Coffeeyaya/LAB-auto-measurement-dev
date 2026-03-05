import sys
import time
import csv
import numpy as np
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from keithley.keithley import Keithley2636B 
from LabAuto.network import Connection 

# -------------------------------
# Worker Thread: Persistent Laser Control
# -------------------------------
class PersistentLaserWorker(QThread):
    """Holds a single socket connection open for the entire sequence."""
    prep_finished = pyqtSignal()
    status_update = pyqtSignal(str) 
    light_turned_on = pyqtSignal() 
    laser_finished = pyqtSignal() # Signals the GUI that the light is safely off and socket is closed

    def __init__(self, light_ip, port=5001, wait_time=3):
        super().__init__()
        self.light_ip = light_ip
        self.port = port
        self.wait_time = wait_time
        self.running = True
        self.sweep_active = False # Flag to hold the connection open during the sweep
        self.conn = None

    def run(self):
        try:
            self.status_update.emit(f"Connecting to Light PC ({self.light_ip})...")
            self.conn = Connection.connect(self.light_ip, self.port)
            
            # 1. Turn ON
            self.status_update.emit("Sending Light ON command...")
            self.conn.send_json({"channel": 6, "wavelength": "660", "power": "17", "on": 1})
            self.conn.receive_json() # Wait for GUI click
            self.light_turned_on.emit() 

            # 2. 30-Second Countdown
            for i in range(self.wait_time, 0, -1):
                if not self.running:
                    self._turn_off_and_close()
                    return 
                self.status_update.emit(f"Light is ON! Waiting {i}s to stabilize...")
                time.sleep(1)
            
            # 3. Trigger Sweep and Hold Connection
            if self.running:
                self.sweep_active = True
                self.status_update.emit("Wait complete. Starting Sweep!")
                self.prep_finished.emit() 
                
                # This loop keeps the thread alive and the socket open while SweepWorker runs
                while self.sweep_active and self.running:
                    time.sleep(0.1)

            # 4. Sweep is done (or aborted), shut down light
            self._turn_off_and_close()

        except Exception as e:
            self.status_update.emit(f"Network Error: {e}")
            if self.conn:
                self.conn.close()
            self.laser_finished.emit()

    def _turn_off_and_close(self):
        """Helper to cleanly turn off the light and drop the socket."""
        if self.conn:
            try:
                self.status_update.emit("Sending Light OFF...")
                self.conn.send_json({"channel": 6, "on": 1})
                self.conn.receive_json()
            except Exception as e:
                print(f"Failed to turn off light: {e}")
            finally:
                self.conn.close()
                self.conn = None
        self.laser_finished.emit()

    def finish_sweep(self):
        """Called by the main GUI when the SweepWorker completes its loop."""
        self.sweep_active = False

    def stop(self):
        """Called if the user hits the Abort button."""
        self.running = False
        self.sweep_active = False
        self.wait()


# -------------------------------
# Worker Thread: Sweep
# -------------------------------
class SweepWorker(QThread):
    new_data = pyqtSignal(float, float, float, float)  
    sweep_finished = pyqtSignal()

    def __init__(self, keithley, vg_points, settle_delay, do_deplete=False):
        super().__init__()
        self.k = keithley
        self.vg_points = vg_points
        self.settle_delay = settle_delay
        self.do_deplete = do_deplete
        self.running = True

    def run(self):
        if self.do_deplete and self.running:
            print("Depleting at -5V for 5 seconds...")
            self.k.set_Vg(-5.0)
            for _ in range(50): 
                if not self.running: break
                time.sleep(0.1)
                
        for vg in self.vg_points:
            if not self.running:
                break 
                
            self.k.set_Vg(vg)
            time.sleep(self.settle_delay)
            I_D, I_G = self.k.measure()
            
            if I_D is not None and self.running:
                self.new_data.emit(self.k.Vd, vg, I_D, I_G)
                
        self.sweep_finished.emit()
                
    def stop(self):
        self.running = False
        self.wait()


# -------------------------------
# PyQt5 GUI
# -------------------------------
class IdVgWindow(QWidget):
    def __init__(self, keithley, filename, light_ip):
        super().__init__()
        self.setWindowTitle("Id-Vg Transfer Characteristics")
        self.k = keithley
        self.csv_file = filename
        self.light_ip = light_ip 
        
        self.light_is_on = False 

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.ax1 = self.figure.add_subplot(111)
        self.ax1.set_title("Steady-State Id-Vg")
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(1.0)

        self.DEPLETE = False
        self.deplete_button = QPushButton("Not deplete")
        self.deplete_button.setCheckable(True)  
        self.deplete_button.clicked.connect(self.toggle_value)

        self.start_btn = QPushButton("Dark Sweep")
        self.light_sweep_btn = QPushButton("Light ON + Sweep") 
        self.stop_btn = QPushButton("Abort")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear Plot")

        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")

        ctrl_layout.addWidget(QLabel("Vd (V):"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addWidget(self.deplete_button)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addWidget(self.clear_btn)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.light_sweep_btn)
        ctrl_layout.addWidget(self.stop_btn)

        self.start_btn.clicked.connect(self.start_sweep)
        self.light_sweep_btn.clicked.connect(self.start_light_prep)
        self.stop_btn.clicked.connect(self.abort_sweep)
        self.clear_btn.clicked.connect(self.clear_plot)

        self.Vgs, self.I_Ds = [], []
        self.worker = None
        self.laser_worker = None
        self.current_line = None 

        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["V_D", "V_G", "I_D", "I_G"])

    def toggle_value(self):
        self.DEPLETE = self.deplete_button.isChecked()
        self.deplete_button.setText("Deplete ON" if self.DEPLETE else "Not deplete")

    def clear_plot(self):
        self.ax1.clear()
        self.ax1.set_title("Steady-State Id-Vg")
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)
        self.canvas.draw()
        
    def mark_light_on(self):
        self.light_is_on = True

    def start_light_prep(self):
        self.start_btn.setEnabled(False)
        self.light_sweep_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)

        # Start the persistent connection thread
        self.laser_worker = PersistentLaserWorker(self.light_ip, wait_time=3)
        self.laser_worker.status_update.connect(self.status_label.setText)
        self.laser_worker.light_turned_on.connect(self.mark_light_on)
        self.laser_worker.prep_finished.connect(self.start_sweep) 
        self.laser_worker.laser_finished.connect(self.on_laser_finished) # Wait for laser off to unlock UI
        self.laser_worker.start()

    def start_sweep(self):
        self.status_label.setText("Status: Sweeping...")
        self.start_btn.setEnabled(False)
        self.light_sweep_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)
        
        self.Vgs.clear()
        self.I_Ds.clear()
        
        V_D = self.Vd_spin.value()
        GATE_START = -3.0
        GATE_STOP = 3.0
        STEPS = 101
        SETTLE_DELAY = 0.1 
        
        self.current_line, = self.ax1.plot([], [], '.-', markersize=8, label=f'Vd = {V_D}V')
        self.ax1.legend() 
        
        vg_points = np.linspace(GATE_START, GATE_STOP, STEPS)
        
        self.k.keithley.write("smua.measure.nplc = 8.0")
        self.k.keithley.write("smub.measure.nplc = 8.0")

        self.k.set_Vd(V_D)
        if not self.DEPLETE:
            self.k.set_Vg(GATE_START)

        self.k.enable_output('a', True)
        self.k.enable_output('b', True)
        self.k.set_autorange('a', 1) #
        self.k.set_autorange('b', 1) #
        
        self.worker = SweepWorker(self.k, vg_points, SETTLE_DELAY, do_deplete=self.DEPLETE)
        self.worker.new_data.connect(self.update_plot)
        self.worker.sweep_finished.connect(self.on_sweep_finished)
        self.worker.start()

    def update_plot(self, Vd, Vg, I_D, I_G):
        self.Vgs.append(Vg)
        self.I_Ds.append(abs(I_D)) 

        if self.current_line:
            self.current_line.set_data(self.Vgs, self.I_Ds)
        
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()

        self.canvas.draw()

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([Vd, Vg, I_D, I_G])

    def abort_sweep(self):
        # 1. Stop Keithley Sweep
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            
        # 2. Stop Laser Worker (this triggers _turn_off_and_close immediately)
        if self.laser_worker and self.laser_worker.isRunning():
            self.status_label.setText("Status: Aborting... Turning Light OFF.")
            self.laser_worker.stop()
        else:
            self.on_sweep_finished() # Just standard cleanup for dark sweep

    def on_sweep_finished(self):
        # 1. Turn off Keithley Outputs
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.enable_output('a', False)
        self.k.enable_output('b', False)
        
        # 2. Instruct PersistentLaserWorker to turn off light
        if self.laser_worker and self.laser_worker.isRunning():
            self.status_label.setText("Status: Sweep Complete. Turning Light OFF...")
            # Changing this flag breaks the hold loop inside the thread, triggering _turn_off_and_close
            self.laser_worker.finish_sweep() 
        else:
            # If it was just a Dark Sweep, we can finalize the UI immediately
            if "Aborting" not in self.status_label.text():
                self.finalize_ui("Status: Finished (Dark)")

    def on_laser_finished(self):
        """Triggered when the PersistentLaserWorker completely finishes closing the connection."""
        self.light_is_on = False
        self.laser_worker = None
        self.finalize_ui("Status: Finished (Light OFF)")

    def finalize_ui(self, status_msg):
        self.status_label.setText(status_msg)
        self.start_btn.setEnabled(True)
        self.light_sweep_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.Vd_spin.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.deplete_button.setEnabled(True)
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.stop()
            
        if hasattr(self, 'laser_worker') and self.laser_worker and self.laser_worker.isRunning():
            self.laser_worker.stop() # Automatically sends OFF command before dying
            
        self.k.shutdown() 
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    run = 0
    device_number = ''
    FILENAME = f'idvg_{device_number}_{run}.csv'
    LIGHT_IP = "192.168.50.17" 
    
    k26 = Keithley2636B(RESOURCE_ID)
    k26.connect()
    k26.clean_instrument()
    k26.config() 

    app = QApplication(sys.argv)
    window = IdVgWindow(k26, filename=FILENAME, light_ip=LIGHT_IP)
    window.show()
    sys.exit(app.exec_())