import sys
import time
import csv
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from keithley.keithley import Keithley2636B
from LabAuto.laser_client import LaserController 

# -------------------------------
# Worker Thread: Unified Hardware Control
# -------------------------------
class IdVgWorker(QThread):
    new_data = pyqtSignal(float, float, float, float)  # Vd, Vg, I_D, I_G
    status_update = pyqtSignal(str)
    sweep_finished = pyqtSignal()

    def __init__(self, resource_id, laser_ip, filename, Vd_target, vg_points, settle_delay, do_deplete=False, laser_cmd=None, light_wait=3):
        super().__init__()
        self.resource_id = resource_id
        self.laser_ip = laser_ip
        self.filename = filename
        self.Vd_target = Vd_target
        self.vg_points = vg_points
        self.settle_delay = settle_delay
        self.do_deplete = do_deplete
        
        self.laser_cmd = laser_cmd 
        self.light_wait = light_wait
        self.running = True

    def run(self):
        k = None
        laser = None
        light_is_on = False

        try:
            self.status_update.emit("Connecting to Keithley...")
            k = Keithley2636B(self.resource_id)
            k.connect()
            k.clean_instrument()
            k.config()
            k.keithley.write("smua.measure.nplc = 8.0")
            k.keithley.write("smub.measure.nplc = 8.0")
            
            k.set_Vd(self.Vd_target)
            k.enable_output('a', True)
            k.enable_output('b', True)
            k.set_autorange('a', 1)
            k.set_autorange('b', 1)

            # --- Laser Preparation (If requested) ---
            if self.laser_cmd and self.running:
                self.status_update.emit(f"Connecting to Light PC ({self.laser_ip})...")
                laser = LaserController(self.laser_ip)
                
                self.status_update.emit("Configuring laser and waiting for GUI...")
                # 1. Set parameters (Synchronous: waits for PyAutoGUI)
                laser.send_cmd(self.laser_cmd, wait_for_reply=True)
                
                # 2. Turn light ON
                self.status_update.emit("Turning light ON...")
                laser.send_cmd({"channel": self.laser_cmd["channel"], "on": 1}, wait_for_reply=True)
                light_is_on = True
                
                # 3. Stabilization countdown
                for i in range(self.light_wait, 0, -1):
                    if not self.running: break
                    self.status_update.emit(f"Light is ON! Stabilizing... {i}s")
                    time.sleep(1)

            # --- Depletion Phase ---
            if self.do_deplete and self.running:
                self.status_update.emit("Depleting at -5V for 5 seconds...")
                k.set_Vg(-5.0)
                for _ in range(50): 
                    if not self.running: break
                    time.sleep(0.1)

            # --- The Id-Vg Sweep ---
            self.status_update.emit("Sweeping...")
            for vg in self.vg_points:
                if not self.running: break
                    
                k.set_Vg(vg)
                time.sleep(self.settle_delay)
                I_D, I_G = k.measure()
                
                if I_D is not None:
                    # Save to CSV
                    with open(self.filename, 'a', newline='') as f:
                        csv.writer(f).writerow([self.Vd_target, vg, I_D, I_G])
                    
                    # Push to GUI
                    self.new_data.emit(self.Vd_target, vg, I_D, I_G)

        except Exception as e:
            print(f"Hardware Error: {e}")
            self.status_update.emit(f"Error: {e}")

        finally:
            self.status_update.emit("Shutting down hardware...")
            if light_is_on and laser:
                # Fire and forget the OFF command
                laser.send_cmd({"channel": self.laser_cmd["channel"], "on": 1}, wait_for_reply=False)
                laser.close()
            if k:
                k.set_Vd(0)
                k.set_Vg(0)
                k.enable_output('a', False)
                k.enable_output('b', False)
                k.shutdown()
                
            self.sweep_finished.emit()

    def stop(self):
        self.running = False
        self.wait()


# -------------------------------
# PyQt5 GUI
# -------------------------------
class IdVgWindow(QWidget):
    def __init__(self, resource_id, filename, light_ip):
        super().__init__()
        self.setWindowTitle("Id-Vg Transfer Characteristics")
        
        self.resource_id = resource_id
        self.csv_file = filename
        self.light_ip = light_ip 
        
        self.Vgs, self.I_Ds = [], []
        self.worker = None
        self.current_line = None 
        self.last_draw_time = time.time() # For frame-rate throttling

        # Ensure CSV exists
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["V_D", "V_G", "I_D", "I_G"])

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Plot Setup
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.ax1 = self.figure.add_subplot(111)
        self._format_axes()

        # Control Panel Setup
        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(1.0)

        self.DEPLETE = False
        self.deplete_button = QPushButton("Not deplete")
        self.deplete_button.setCheckable(True)  
        self.deplete_button.clicked.connect(self.toggle_deplete)

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

        # Connect Buttons
        self.start_btn.clicked.connect(self.start_dark_sweep)
        self.light_sweep_btn.clicked.connect(self.start_light_sweep)
        self.stop_btn.clicked.connect(self.abort_sweep)
        self.clear_btn.clicked.connect(self.clear_plot)

    def _format_axes(self):
        self.ax1.set_title("Steady-State Id-Vg")
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

    def toggle_deplete(self):
        self.DEPLETE = self.deplete_button.isChecked()
        self.deplete_button.setText("Deplete ON" if self.DEPLETE else "Not deplete")

    def clear_plot(self):
        self.ax1.clear()
        self._format_axes()
        self.canvas.draw()
        
    def start_sweep_common(self, is_light_sweep):
        """Helper to launch the background worker for either mode."""
        # Lock UI
        self.start_btn.setEnabled(False)
        self.light_sweep_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)
        
        self.Vgs.clear()
        self.I_Ds.clear()
        
        V_D = self.Vd_spin.value()
        vg_points = np.linspace(-3.0, 3.0, 101) # Edit bounds here if needed
        
        # Setup the plot line for this specific run
        label = f'Vd = {V_D}V (Light)' if is_light_sweep else f'Vd = {V_D}V (Dark)'
        self.current_line, = self.ax1.plot([], [], '.-', markersize=8, label=label)
        self.ax1.legend()
        
        # Define laser command if it's a light sweep
        laser_cmd = {"channel": 6, "wavelength": 660, "power": 17} if is_light_sweep else None

        # Launch unified worker
        self.worker = IdVgWorker(
            resource_id=self.resource_id,
            laser_ip=self.light_ip,
            filename=self.csv_file,
            Vd_target=V_D,
            vg_points=vg_points,
            settle_delay=0.1,
            do_deplete=self.DEPLETE,
            laser_cmd=laser_cmd,
            light_wait=3
        )
        
        self.worker.new_data.connect(self.update_plot)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.sweep_finished.connect(self.on_sweep_finished)
        self.worker.start()

    def start_dark_sweep(self):
        self.start_sweep_common(is_light_sweep=False)

    def start_light_sweep(self):
        self.start_sweep_common(is_light_sweep=True)

    def update_plot(self, Vd, Vg, I_D, I_G):
        """Safely updates memory and throttles the screen redraw to prevent lagging."""
        self.Vgs.append(Vg)
        self.I_Ds.append(abs(I_D)) 

        self.current_line.set_data(self.Vgs, self.I_Ds)
        
        # Frame-rate throttle (max 10 fps)
        current_time = time.time()
        if current_time - self.last_draw_time > 0.1:
            if self.ax1.get_autoscale_on():
                self.ax1.relim()
                self.ax1.autoscale_view()
            self.canvas.draw()
            self.last_draw_time = current_time

    def abort_sweep(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Status: Aborting...")
            self.worker.stop()

    def on_sweep_finished(self):
        # Final redraw to guarantee the last few points are drawn
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()
        self.canvas.draw()
        
        self.status_label.setText("Status: Finished")
        
        # Unlock UI
        self.start_btn.setEnabled(True)
        self.light_sweep_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.Vd_spin.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.deplete_button.setEnabled(True)
        
    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait() # Ensure hardware powers down before the window dies
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    LIGHT_IP = "192.168.50.17" 
    
    device_number = 'A1'
    run = 0
    FILENAME = f'idvg_{device_number}_{run}.csv'

    app = QApplication(sys.argv)
    
    # We now pass the RESOURCE_ID directly to the window, 
    # letting the background thread spawn its own Keithley connection!
    window = IdVgWindow(RESOURCE_ID, filename=FILENAME, light_ip=LIGHT_IP)
    window.show()
    
    sys.exit(app.exec_())