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

from keithley import Keithley2636B 

# -------------------------------
# Worker Thread for Sweep
# -------------------------------
class SweepWorker(QThread):
    # Emits: Vd, Vg, I_D, I_G
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
        # --- DEPLETION PHASE ---
        if self.do_deplete and self.running:
            print("Depleting at -5V for 5 seconds...")
            self.k.set_Vg(-5.0)
            
            # Break the 5 seconds into small chunks so "Abort" is responsive
            for _ in range(50): 
                if not self.running: break
                time.sleep(0.1)
                
        # --- SWEEP PHASE ---
        for vg in self.vg_points:
            if not self.running:
                break 
                
            # 1. Step the Gate Voltage
            self.k.set_Vg(vg)
            
            # 2. Wait peacefully for the RC circuit to settle
            time.sleep(self.settle_delay)
            
            # 3. Measure exactly once per step
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
    def __init__(self, keithley, filename):
        super().__init__()
        self.setWindowTitle("Id-Vg Transfer Characteristics")
        self.k = keithley
        self.csv_file = filename

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Setup Single Plot 
        self.ax1 = self.figure.add_subplot(111)
        self.ax1.set_title("Steady-State Id-Vg")
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

        # Deplete Toggle
        self.DEPLETE = False
        self.deplete_button = QPushButton("Not deplete")
        self.deplete_button.setCheckable(True)  
        self.deplete_button.clicked.connect(self.toggle_value)

        self.start_btn = QPushButton("Start Sweep")
        self.stop_btn = QPushButton("Abort")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear Plot")

        ctrl_layout.addWidget(QLabel("Constant Vd (V):"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addWidget(self.deplete_button)
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
        self.current_line = None 

        # Setup CSV Header
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

    def start_sweep(self):
        # 1. Prepare UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)
        
        # Clear data arrays for the NEW sweep
        self.Vgs.clear()
        self.I_Ds.clear()
        
        # 2. Setup Sweep Parameters
        V_D = self.Vd_spin.value()
        GATE_START = -3.0
        GATE_STOP = 3.0
        STEPS = 21
        SETTLE_DELAY = 0.5 # A solid half-second wait for clean data
        
        self.current_line, = self.ax1.plot([], [], '.-', markersize=8, label=f'Vd = {V_D}V')
        self.ax1.legend() 
        
        vg_points = np.linspace(GATE_START, GATE_STOP, STEPS)
        
        # 3. Configure Instrument
        # self.k.keithley.write("smua.measure.autorangei = 1")
        # self.k.keithley.write("smub.measure.autorangei = 1")
        # NPLC 8.0 is great for low-noise Id-Vg when you aren't rushing for transient data
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
        
    def closeEvent(self, event):
        """Safely shuts down hardware when the window is closed."""
        print("Closing application. Safely shutting down hardware...")
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        self.k.shutdown() 
        event.accept()

# -------------------------------
# Run Application
# -------------------------------
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    FILENAME = 'idvg_gui_data.csv'
    
    k26 = Keithley2636B(RESOURCE_ID)
    k26.connect()
    k26.clean_instrument()
    k26.config() 

    app = QApplication(sys.argv)
    window = IdVgWindow(k26, filename=FILENAME)
    window.show()
    sys.exit(app.exec_())