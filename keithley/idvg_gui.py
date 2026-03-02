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
    # Signal 1: Emits continuously (Time, Vd, Vg, Id, Ig)
    transient_data = pyqtSignal(float, float, float, float, float)  
    
    # Signal 2: Emits ONLY the final settled value (Time, Vd, Vg, Id, Ig)
    steady_data = pyqtSignal(float, float, float, float, float)
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
        start_time = time.time()
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
            # instead of time.sleep(self.settle_delay), we measure the transient response
            # --- THE TRANSIENT POLLING LOOP ---
            step_end_time = time.time() + self.settle_delay
            last_Id = None

            while time.time() < step_end_time:
                if not self.running:
                    break
                    
                I_D, I_G = self.k.measure()
                if I_D is not None:
                    t = time.time() - start_time
                    # Emit to the Transient Graph continuously
                    self.transient_data.emit(t, self.k.Vd, vg, I_D, I_G)
                    last_Id = I_D # Keep track of the most recent value
                    last_Ig = I_G # Keep track of the most recent value

            # --- THE STEADY STATE EMIT ---
            # Once the time is up, emit the very last measured value to the Id-Vg graph
            if last_Id is not None and self.running:
                self.steady_data.emit(t, self.k.Vd, vg, last_Id, last_Ig)
                
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
        self.setWindowTitle("Id-Vg & Transient")
        self.k = keithley
        self.csv_file = filename
        self.transient_csv_file = filename.replace('.csv', '_transient.csv')

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Matplotlib Figure (Made wider to fit two plots)
        self.figure = Figure(figsize=(12, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # --- PLOT 1: Steady State Id-Vg ---
        self.ax_steady = self.figure.add_subplot(121)
        self.ax_steady.set_title("Steady-State Id-Vg")
        self.ax_steady.set_ylabel("Drain Current (A)", color='b')
        self.ax_steady.set_xlabel("Gate Voltage (V)")
        self.ax_steady.set_yscale('log')
        self.ax_steady.grid(True, which="both", ls="--", alpha=0.5)

        # --- PLOT 2: Transient Id-Time ---
        self.ax_trans = self.figure.add_subplot(122)
        self.ax_trans.set_title("Transient Response")
        self.ax_trans.set_ylabel("Drain Current (A)", color='r')
        self.ax_trans.set_xlabel("Time (s)")
        self.ax_trans.set_yscale('log')
        self.ax_trans.grid(True, which="both", ls="--", alpha=0.5)

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
        self.clear_btn = QPushButton("Clear Plot") 

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
        self.Vgs_steady, self.Ids_steady = [], []
        self.times_trans, self.Ids_trans = [], []
        self.worker = None
        self.line_steady = None 
        self.line_trans = None 

        # Setup CSV Headers
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])
                
        if not os.path.exists(self.transient_csv_file):
            with open(self.transient_csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

        # Deplete button                
        self.DEPLETE = False
        self.deplete_button = QPushButton("Not deplete")
        self.deplete_button.setCheckable(True) 
        self.deplete_button.clicked.connect(self.toggle_value)
        ctrl_layout.insertWidget(2, self.deplete_button) # Added inline nicely

    def toggle_value(self):
        self.DEPLETE = self.deplete_button.isChecked()
        self.deplete_button.setText("Deplete ON" if self.DEPLETE else "Not deplete")

    def clear_plot(self):
        self.ax_steady.clear()
        self.ax_steady.set_title("Steady-State Id-Vg")
        self.ax_steady.set_ylabel("Drain Current (A)", color='b')
        self.ax_steady.set_xlabel("Gate Voltage (V)")
        self.ax_steady.set_yscale('log')
        self.ax_steady.grid(True, which="both", ls="--", alpha=0.5)
        
        self.ax_trans.clear()
        self.ax_trans.set_title("Transient Response")
        self.ax_trans.set_ylabel("Drain Current (A)", color='r')
        self.ax_trans.set_xlabel("Time (s)")
        self.ax_trans.set_yscale('log')
        self.ax_trans.grid(True, which="both", ls="--", alpha=0.5)
        
        self.canvas.draw()

    def start_sweep(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.Vd_spin.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.deplete_button.setEnabled(False)
        
        # Clear data arrays for the NEW sweep
        self.Vgs_steady.clear()
        self.Ids_steady.clear()
        self.times_trans.clear()
        self.Ids_trans.clear()
        
        V_D = self.Vd_spin.value()
        GATE_START = -3.0
        GATE_STOP = 3.0
        STEPS = 21
        
        # NOTE: Consider increasing SETTLE_DELAY and lowering NPLC to see a true transient curve
        SETTLE_DELAY = 3.0 
        
        # Create lines for BOTH plots
        self.line_steady, = self.ax_steady.plot([], [], 'b.-', markersize=8, label=f'Vd = {V_D}V')
        self.line_trans, = self.ax_trans.plot([], [], 'r.-', markersize=4, alpha=0.7, label=f'Vd = {V_D}V')
        self.ax_steady.legend() 
        self.ax_trans.legend() 
        
        vg_points = np.linspace(GATE_START, GATE_STOP, STEPS)
        
        # Configure Instrument
        # self.k.keithley.write("smua.measure.autorangei = 1")
        # self.k.keithley.write("smub.measure.autorangei = 1")
        self.k.keithley.write("smua.measure.nplc = 0.1")
        self.k.keithley.write("smub.measure.nplc = 0.1")
    
        self.k.set_Vd(V_D)
        if not self.DEPLETE:
            self.k.set_Vg(GATE_START)

        self.k.enable_output('a', True)
        self.k.enable_output('b', True)
        
        # Start Thread
        self.worker = SweepWorker(self.k, vg_points, SETTLE_DELAY, do_deplete=self.DEPLETE)
        
        # CONNECT TO THE TWO SEPARATE FUNCTIONS
        self.worker.transient_data.connect(self.update_transient_plot)
        self.worker.steady_data.connect(self.update_steady_plot)
        
        self.worker.sweep_finished.connect(self.on_sweep_finished)
        self.worker.start()

    def update_transient_plot(self, t, Vd, Vg, I_D, I_G):
        self.times_trans.append(t)
        self.Ids_trans.append(abs(I_D)) 

        if self.line_trans:
            self.line_trans.set_data(self.times_trans, self.Ids_trans)
        
        if self.ax_trans.get_autoscale_on():
            self.ax_trans.relim()
            self.ax_trans.autoscale_view()

        self.canvas.draw()

        with open(self.transient_csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t, Vd, Vg, I_D, I_G])

    def update_steady_plot(self, t, Vd, Vg, I_D, I_G):
        self.Vgs_steady.append(Vg)
        self.Ids_steady.append(abs(I_D)) 

        if self.line_steady:
            self.line_steady.set_data(self.Vgs_steady, self.Ids_steady)
        
        if self.ax_steady.get_autoscale_on():
            self.ax_steady.relim()
            self.ax_steady.autoscale_view()

        self.canvas.draw()

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t, Vd, Vg, I_D, I_G])

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
        self.setWindowTitle("Id-Vg & Transient Sweep - Finished")

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