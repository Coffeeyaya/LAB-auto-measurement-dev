import sys
import time
import csv
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel, QSpinBox)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from keithley import Keithley2636B # Ensure your class has set_Vd, set_Vg, and measure
import os
# -------------------------------
# Worker Thread for Sweep
# -------------------------------
class SweepWorker(QThread):
    new_data = pyqtSignal(float, float, float)  
    sweep_finished = pyqtSignal()

    # ADD 'do_deplete' to the arguments
    def __init__(self, keithley, vg_points, settle_delay, do_deplete=False):
        super().__init__()
        self.k = keithley
        self.vg_points = vg_points
        self.settle_delay = settle_delay
        self.do_deplete = do_deplete # Store the boolean
        self.running = True

    def run(self):
        # --- DEPLETION PHASE ---
        if self.do_deplete and self.running:
            print("Depleting at -5V for 5 seconds...")
            self.k.set_Vg(-5.0)
            
            # We break the 5 seconds into small chunks. 
            # This allows the user to click "Abort" DURING the 5 second wait!
            for _ in range(50): 
                if not self.running: break
                time.sleep(0.1)
                
        # --- SWEEP PHASE ---
        for vg in self.vg_points:
            if not self.running:
                break 
                
            self.k.set_Vg(vg)
            time.sleep(self.settle_delay)
            I_D, I_G = self.k.measure()
            
            if I_D is not None:
                self.new_data.emit(vg, I_D, I_G)
                
        self.sweep_finished.emit()
    def stop(self):
        self.running = False
        self.wait()

# -------------------------------
# PyQt5 GUI
# -------------------------------


class IdVgWindow(QWidget):
    def __init__(self, keithley, filename):
        super().__init__()
        self.setWindowTitle("Id-Vg Transfer Characteristics")
        self.k = keithley
        self.csv_file = filename

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Matplotlib Figure
        self.figure = Figure(figsize=(7,5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Setup Plot 
        self.ax1 = self.figure.add_subplot(111)
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)

        # Controls Layout
        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        # Vd Input
        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(1.0)

        self.start_btn = QPushButton("Start Sweep")
        self.stop_btn = QPushButton("Abort")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear Plot") # New Button

        ctrl_layout.addWidget(QLabel("Constant Vd (V):"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.clear_btn)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)

        # Connect signals
        self.start_btn.clicked.connect(self.start_sweep)
        self.stop_btn.clicked.connect(self.abort_sweep)
        self.clear_btn.clicked.connect(self.clear_plot)

        # Data storage
        self.Vgs, self.I_Ds = [], []
        self.worker = None
        self.current_line = None # Tracks the active line being drawn

        # Setup CSV Header (Only write if file doesn't exist or we want a fresh one)
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["V_D", "V_G", "I_D", "I_G"])

        # deplete button                
        self.DEPLETE = False

        self.deplete_button = QPushButton("Not deplete")
        self.deplete_button.setCheckable(True)  # Makes it toggleable
        self.deplete_button.clicked.connect(self.toggle_value)

        layout.addWidget(self.deplete_button)

    def toggle_value(self):
        self.DEPLETE = self.deplete_button.isChecked()
        self.deplete_button.setText("Deplete" if self.DEPLETE else "Not deplete")
        print("Boolean value:", self.DEPLETE)

    def clear_plot(self):
        """Removes all lines from the plot and resets the view."""
        self.ax1.clear()
        self.ax1.set_ylabel("Drain Current (A) - Log", color='b')
        self.ax1.set_xlabel("Gate Voltage (V)")
        self.ax1.set_yscale('log')
        self.ax1.grid(True, which="both", ls="--", alpha=0.5)
        self.canvas.draw()

    def start_sweep(self):
        # 1. Prepare UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)
        
        
        # Clear data arrays for the NEW sweep, but DO NOT clear the plot
        self.Vgs.clear()
        self.I_Ds.clear()
        
        # 2. Setup Sweep Parameters
        V_D = self.Vd_spin.value()
        GATE_START = -3.0
        GATE_STOP = 3.0
        STEPS = 21
        SETTLE_DELAY = 0.1
        
        # Create a new line on the plot for this specific Vd sweep
        # Matplotlib will automatically cycle the colors for you!
        self.current_line, = self.ax1.plot([], [], '.-', markersize=8, label=f'Vd = {V_D}V')
        self.ax1.legend() # Update legend to show the new line
        
        vg_points = np.linspace(GATE_START, GATE_STOP, STEPS)
        
        # 3. Configure Instrument
        self.k.keithley.write("smua.measure.autorangei = 1")
        self.k.keithley.write("smub.measure.autorangei = 1")
        self.k.keithley.write("smua.measure.nplc = 8.0") 
        self.k.keithley.write("smub.measure.nplc = 8.0")
    

        self.k.set_Vd(V_D)

        if not self.DEPLETE:
            self.k.set_Vg(GATE_START)

        self.k.enable_output('a', True)
        self.k.enable_output('b', True)
        
        # 4. Start Thread
        self.worker = SweepWorker(self.k, vg_points, SETTLE_DELAY, do_deplete=self.DEPLETE)
        self.worker.new_data.connect(self.update_plot)
        self.worker.sweep_finished.connect(self.on_sweep_finished)
        self.worker.start()

    def update_plot(self, Vg, I_D, I_G):
        self.Vgs.append(Vg)
        self.I_Ds.append(abs(I_D)) 

        # Update ONLY the active line for this sweep
        if self.current_line:
            self.current_line.set_data(self.Vgs, self.I_Ds)
        
        if self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()

        self.canvas.draw()

        # Save to CSV using APPEND mode ('a') so we don't overwrite previous sweeps
        V_D = self.Vd_spin.value()
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([V_D, Vg, I_D, I_G])

    def abort_sweep(self):
        if self.worker:
            self.worker.stop()
        self.on_sweep_finished()

    def on_sweep_finished(self):
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.enable_output('a', False)
        self.k.enable_output('b', False)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.Vd_spin.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.deplete_button.setEnabled(True)
        self.setWindowTitle("Id-Vg Sweep - Finished")

# -------------------------------
# Run Application
# -------------------------------
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    FILENAME = 'idvg_gui_data.csv'
    
    k26 = Keithley2636B(RESOURCE_ID)
    k26.connect()
    k26.clean_instrument()
    
    # Base config (Limits)
    k26.config() 

    app = QApplication(sys.argv)
    window = IdVgWindow(k26, filename=FILENAME)
    window.show()
    sys.exit(app.exec_())