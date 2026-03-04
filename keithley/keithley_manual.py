import sys
import time
import csv
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel, QLineEdit)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from keithley import Keithley2636B

# -------------------------------
# Worker Thread for Measurement
# -------------------------------
class KeithleyWorker(QThread):
    new_data = pyqtSignal(float, float, float, float, float)  # time, Vd, Vg, I_D, I_G

    def __init__(self, keithley):
        super().__init__()
        self.k = keithley
        self.running = True

    def run(self):
        start_time = time.time()
        while self.running:
            # Because of the lock we built into Keithley2636B, this measure command 
            # will politely wait for a fraction of a millisecond if the user 
            # clicks "Set Vg" or if the Pulse thread is changing the voltage!
            I_D, I_G = self.k.measure()
            
            t = time.time() - start_time
            # Grab the current Vd and Vg state from the class variables
            self.new_data.emit(t, self.k.Vd, self.k.Vg, I_D, I_G) 
            self.msleep(100)  # 10 Hz

    def stop(self):
        self.running = False
        self.wait()

# -------------------------------
# PyQt5 GUI
# -------------------------------
class MainWindow(QWidget):
    def __init__(self, keithley):
        super().__init__()
        self.setWindowTitle("Keithley Real-Time Dashboard")
        self.k = keithley

        # Layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Initialize modules
        self._setup_plots()
        self._setup_controls()
        
        # Memory allocation
        self.times, self.I_Ds, self.I_Gs, self.V_Ds, self.V_Gs = [], [], [], [], []

    def _setup_plots(self):
        self.figure = Figure(figsize=(10,7))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.canvas)

        # Current axes (Left)
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        self.ax1.set_ylabel("I_D (A)", color='blue')
        self.ax2.set_ylabel("I_G (A)", color='red')
        self.ax2.set_xlabel("Time (s)")
        
        # Voltage axes (Right)
        self.ax1_v = self.ax1.twinx() 
        self.ax1_v.set_ylabel('V_D (V)', color='lightblue')
        
        self.ax2_v = self.ax2.twinx()
        self.ax2_v.set_ylabel('V_G (V)', color='lightcoral')

        self.ax1.legend(loc='upper left')
        self.ax1_v.legend(loc='upper right')
        self.ax2.legend(loc='upper left')
        self.ax2_v.legend(loc='upper right')

    def _setup_controls(self):
        ctrl_layout = QHBoxLayout()
        self.main_layout.addLayout(ctrl_layout)

        # --- Block 1: Measurement & File ---
        self.filename_input = QLineEdit("time_dep_1.csv")
        self.start_measure_btn = QPushButton("Start Measure")
        self.stop_btn = QPushButton("Stop All")
        self.stop_btn.setEnabled(False)

        # --- Block 2: Manual Control ---
        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(self.k.Vd)

        self.Vg_spin = QDoubleSpinBox()
        self.Vg_spin.setRange(-10.0, 10.0)
        self.Vg_spin.setSingleStep(0.1)
        self.Vg_spin.setValue(self.k.Vg)

        self.set_Vd_btn = QPushButton("Set Vd")
        self.set_Vg_btn = QPushButton("Set Vg")
        
        # --- Block 3: Automation ---
        self.pulse_btn = QPushButton("Start Vg Pulse")
        self.pulse_btn.setEnabled(False) # Only enable when measuring!

        # Add to layout horizontally
        ctrl_layout.addWidget(QLabel("File:"))
        ctrl_layout.addWidget(self.filename_input)
        ctrl_layout.addWidget(self.start_measure_btn)
        
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(QLabel("Vd:"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addWidget(self.set_Vd_btn)
        
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(QLabel("Vg:"))
        ctrl_layout.addWidget(self.Vg_spin)
        ctrl_layout.addWidget(self.set_Vg_btn)
        
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(self.pulse_btn)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.stop_btn)

        # Connections
        self.start_measure_btn.clicked.connect(self.start_measurement)
        self.set_Vd_btn.clicked.connect(self.apply_Vd)
        self.set_Vg_btn.clicked.connect(self.apply_Vg)
        self.pulse_btn.clicked.connect(self.trigger_pulse)
        self.stop_btn.clicked.connect(self.stop_everything)

    def _setup_data_pipeline(self, filename):
        self.times, self.I_Ds, self.I_Gs = [], [], []
        self.V_Ds, self.V_Gs = [], []

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

    # --- BUTTON ACTIONS ---

    def start_measurement(self):
        # 1. UI Updates
        self.start_measure_btn.setEnabled(False)
        self.filename_input.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pulse_btn.setEnabled(True) # Now we can pulse!
        
        # 2. Pipeline & Plot Initialization
        self.filename = self.filename_input.text()
        self._setup_data_pipeline(self.filename)
        
        run_name = self.filename.replace('.csv', '')
        self.line_id, = self.ax1.plot([], [], 'b.-', label=f'I_D ({run_name})')
        self.line_ig, = self.ax2.plot([], [], 'r.-', label=f'I_G ({run_name})')
        self.line_vd, = self.ax1_v.plot([], [], 'g.-', alpha=0.3, label='V_D')
        self.line_vg, = self.ax2_v.plot([], [], 'k.-', alpha=0.3, label='V_G')
        
        self.ax1.legend(loc='upper left'); self.ax2.legend(loc='upper left')
        self.ax1_v.legend(loc='upper right'); self.ax2_v.legend(loc='upper right')
        
        # 3. Hardware Setup (Apply current spinbox values and turn ON)
        self.k.set_Vd(self.Vd_spin.value())
        self.k.set_Vg(self.Vg_spin.value())
        self.k.enable_output('a', True)
        self.k.enable_output('b', True)

        # 4. Start recording thread
        self.worker = KeithleyWorker(self.k)
        self.worker.new_data.connect(self.update_plot)
        self.worker.start()

    def apply_Vd(self):
        value = self.Vd_spin.value()
        self.k.set_Vd(value)
        print(f"Manual override: Vd set to {value} V")

    def apply_Vg(self):
        value = self.Vg_spin.value()
        self.k.set_Vg(value)
        print(f"Manual override: Vg set to {value} V")

    def trigger_pulse(self):
        """Triggers the background pulse sequence."""
        sequence = [(0, 3.0), (1, 3.0), (2, 3.0), (3, 3.0), (2, 3.0), (1, 3.0), (0, 3.0)]
        self.k.start_vg_pulse(sequence)
        self.pulse_btn.setText("Pulsing...")
        self.pulse_btn.setEnabled(False)

    def update_plot(self, t, Vd, Vg, I_D, I_G):
        # Update memory
        self.times.append(t)
        self.V_Ds.append(Vd)
        self.V_Gs.append(Vg)
        self.I_Ds.append(I_D)
        self.I_Gs.append(I_G)
        
        # Plot update
        self.line_vd.set_data(self.times, self.V_Ds)
        self.line_vg.set_data(self.times, self.V_Gs)
        self.line_id.set_data(self.times, self.I_Ds)
        self.line_ig.set_data(self.times, self.I_Gs)
        
        # Autoscale logic
        for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
            if ax.get_autoscale_on():
                ax.relim()
                ax.autoscale_view()
        self.canvas.draw()

        # Save to CSV
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t, Vd, Vg, I_D, I_G])

    def stop_everything(self):
        # 1. Stop data recording
        if hasattr(self, 'worker'):
            self.worker.stop()
            
        # 2. Stop pulse thread (if it is running)
        self.k.stop_vg_pulse()
        
        # 3. Hardware safe shutdown
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.enable_output('a', False)
        self.k.enable_output('b', False)

        # 4. Reset UI
        self.start_measure_btn.setEnabled(True)
        self.filename_input.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pulse_btn.setEnabled(False)
        self.pulse_btn.setText("Start Vg Pulse")

    def closeEvent(self, event):
        print("Closing application. Safely shutting down hardware...")
        self.stop_everything()
        self.k.shutdown() 
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    
    k26 = Keithley2636B(RESOURCE_ID)
    k26.connect()
    k26.clean_instrument()
    
    # Crucial for time-dependent: NPLC determines measurement speed.
    # 1.0 is a good balance between speed and noise for a 10Hz sampling rate.
    k26.config()
    k26.keithley.write("smua.measure.nplc = 1.0") 
    k26.keithley.write("smub.measure.nplc = 1.0")

    app = QApplication(sys.argv)
    window = MainWindow(k26)
    window.show()
    sys.exit(app.exec_())