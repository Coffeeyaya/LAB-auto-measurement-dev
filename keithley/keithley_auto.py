'''
vg pulse automation
'''
import sys
import time
import csv
import pyvisa
from keithley import Keithley2636B

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

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
            I_D, I_G = self.k.measure()
            t = time.time() - start_time
            self.new_data.emit(t, self.k.Vd, self.k.Vg, I_D, I_G) # (Time, V_D, V_G, I_D, I_G)
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
        self.setWindowTitle("Keithley python Control")
        self.k = keithley
        self.filename = 'test.csv'

        # Layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Initialize all the separate modules
        self._setup_plots()
        self._setup_controls()
        self._setup_data_pipeline()

        # measurement
        # self._start_worker_and_sequence()

    def _setup_plots(self):
        """
        Handles everything related to Matplotlib
        """
        self.figure = Figure(figsize=(10,7))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.main_layout.addWidget(self.canvas)
        self.main_layout.addWidget(self.toolbar)

        # current(I_D, I_G) axes: left side
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        self.ax1.set_ylabel("I_D (A)")
        self.ax2.set_ylabel("I_G (A)")
        self.ax2.set_xlabel("Time (s)")
        # self.line_id, = self.ax1.plot([], [], 'b.-', label='I_D')
        # self.line_ig, = self.ax2.plot([], [], 'r.-', label='I_G')
        
        # voltage(V_D, V_G) axes: right side
        self.ax1_v = self.ax1.twinx() 
        self.ax1_v.set_ylabel('V_D (V)', color='lightblue')
        self.ax1_v.tick_params(axis='y', labelcolor='lightblue')

        self.ax2_v = self.ax2.twinx()
        self.ax2_v.set_ylabel('V_G (V)', color='lightcoral')
        self.ax2_v.tick_params(axis='y', labelcolor='lightcoral')

        # self.line_vd, = self.ax1_v.plot([], [], 'g.-', alpha=0.3, label='V_D')
        # self.line_vg, = self.ax2_v.plot([], [], 'k.-', alpha=0.3, label='V_G')

        self.ax1.legend(loc='upper left')
        self.ax1_v.legend(loc='upper right')
        self.ax2.legend(loc='upper left')
        self.ax2_v.legend(loc='upper right')

    def _setup_controls(self):
        """
        Handles buttons, spinboxes and user inputs
        """
        ctrl_layout = QHBoxLayout()
        self.main_layout.addLayout(ctrl_layout) # add control layout to main_layout

        # start button and filename
        self.filename_input = QLineEdit("measurement_1.csv")
        self.start_btn = QPushButton("Start Run")

        ctrl_layout.addWidget(QLabel("Save As:"))
        ctrl_layout.addWidget(self.filename_input)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addSpacing(20)

        # spinboxes for setting Vd and Vg
        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(self.k.Vd) # initial value of the spinbox

        self.Vg_spin = QDoubleSpinBox()
        self.Vg_spin.setRange(-10.0, 10.0)
        self.Vg_spin.setSingleStep(0.1)
        self.Vg_spin.setValue(self.k.Vg)

        # buttons for setting Vd and Vg
        self.set_Vd_btn = QPushButton("Set Vd")
        self.set_Vg_btn = QPushButton("Set Vg")
        self.stop_btn = QPushButton("Stop/Abort")
        self.stop_btn.setEnabled(False) # Disable until a run starts

        # add above spinboxes and buttons to control_layout
        ctrl_layout.addWidget(QLabel("Vd:"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addWidget(self.set_Vd_btn)
        ctrl_layout.addSpacing(20) # Adds visual breathing room
        ctrl_layout.addWidget(QLabel("Vg:"))
        ctrl_layout.addWidget(self.Vg_spin)
        ctrl_layout.addWidget(self.set_Vg_btn)
        ctrl_layout.addStretch() # Pushes the stop button to the far right
        ctrl_layout.addWidget(self.stop_btn)

        # Connect signals
        self.start_btn.clicked.connect(self.start_new_run)
        self.set_Vd_btn.clicked.connect(self.apply_Vd)
        self.set_Vg_btn.clicked.connect(self.apply_Vg)
        self.stop_btn.clicked.connect(self.stop)

    def _setup_data_pipeline(self):
        """
        Initializes memory arrays and the CSV file
        """
        self.times, self.I_Ds, self.I_Gs = [], [], []
        self.V_Ds, self.V_Gs = [], []

        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_D", "V_G", "I_D", "I_G"])

    def _start_worker_and_sequence(self):
        """
        Boots up the background thread and initial pulses
        """
        self.worker = KeithleyWorker(self.k)
        self.worker.new_data.connect(self.update_plot)
        self.worker.start()

        self.k.enable_output('a', True)
        self.k.enable_output('b', True)

        sequence = [(1, 10.0), (-1, 10.0)]
        self.k.set_Vd(1.0)
        self.k.start_vg_pulse(sequence)

    # Apply Set button values
    def apply_Vd(self):
        value = self.Vd_spin.value()
        self.k.set_Vd(value)
        print(f"Vd set to {value} V")

    def apply_Vg(self):
        value = self.Vg_spin.value()
        self.k.set_Vg(value)
        print(f"Vg set to {value} V")

    def start_new_run(self):
        # 1. Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.filename_input.setEnabled(False)
        
        # 2. Get the new filename and initialize the data pipeline
        self.filename = self.filename_input.text()
        self._setup_data_pipeline() # This conveniently resets self.times, self.I_Ds, etc., to empty!
        
        # 3. Create NEW line objects for this specific run
        # Matplotlib will automatically color-cycle these new lines so they stand out
        run_name = self.filename.replace('.csv', '') # delete the file extension, so the the label looks nicer
        self.line_id, = self.ax1.plot([], [], '.-', label=f'I_D ({run_name})')
        self.line_ig, = self.ax2.plot([], [], '.-', label=f'I_G ({run_name})')
        
        # Optional: You can also create new lines for Vd/Vg, but 4 lines per run 
        # can get very visually cluttered on a single graph!
        self.line_vd, = self.ax1_v.plot([], [], '.-', alpha=0.3, label=f'V_D')
        self.line_vg, = self.ax2_v.plot([], [], '.-', alpha=0.3, label=f'V_G')
        
        # Refresh legends to show the new run
        self.ax1.legend(loc='upper left')
        self.ax2.legend(loc='upper left')
        
        # 4. Boot up the background thread and pulse sequence
        self._start_worker_and_sequence()

    def update_plot(self, t, Vd, Vg, I_D, I_G):
        """
        update plot and csv file
        """
        # append data
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

    def stop(self):
        # Stop the worker thread
        self.worker.stop()

        # stop pulse function
        self.k.stop_vg_pulse()

       # Safely zero the outputs, but DO NOT close the connection
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.enable_output('a', False)
        self.k.enable_output('b', False)

        # Re-enable the start controls for the next run
        self.start_btn.setEnabled(True)
        self.filename_input.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # # Disable buttons and spin boxes so user cannot change anymore
        # for widget in [self.set_Vd_btn, self.set_Vg_btn, self.Vd_spin, self.Vg_spin, self.stop_btn]:
        #     widget.setEnabled(False)
    def closeEvent(self, event):
        """
        This triggers automatically when the window is closed (the red X).
        """
        print("Closing application. Safely shutting down hardware...")
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        
        # Stop Keithley pulse thread
        self.k.stop_vg_pulse()

        self.k.shutdown() # This will zero V, turn off output, and close PyVISA
        event.accept()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    keithley = Keithley2636B(RESOURCE_ID)
    keithley.connect()
    keithley.clean_instrument()
    keithley.config()

    app = QApplication(sys.argv)
    window = MainWindow(keithley)
    window.show()
    sys.exit(app.exec_())
