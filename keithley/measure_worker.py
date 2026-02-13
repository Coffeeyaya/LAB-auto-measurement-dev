import sys
import threading
import time
import csv
import os
from keithley import Keithley_2636B

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QSpinBox, QLabel, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtCore import pyqtSignal, QObject

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MeasurementWorker(threading.Thread):
    def __init__(self, keithley_instance, interval=0.1):
        super().__init__()
        self.k = keithley_instance
        self.interval = interval
        self._stop_event = threading.Event()
        self.start_time = time.time()
        self.data = []

        # Prepare CSV
        with open(self.k.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Drain", "V_Gate", "I_Drain", "I_Gate"])

    def run(self):
        while not self._stop_event.is_set():
            t = time.time() - self.start_time
            I_drain, I_gate = self.k.measure()
            self.data.append((t, self.k.Vd, self.k.Vg, I_drain, I_gate))

            # Write to CSV
            with open(self.k.filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([t, self.k.Vd, self.k.Vg, I_drain, I_gate])

            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()
        self.join()


class MainWindow(QMainWindow):
    def __init__(self, keithley_instance):
        super().__init__()
        self.k = keithley_instance
        self.meas_worker = MeasurementWorker(self.k)
        self.vg_pulse_worker = None

        self.setWindowTitle("Keithley Control")
        self.setGeometry(100, 100, 800, 600)

        # --- Central Widget ---
        central = QWidget()
        layout = QVBoxLayout()

        # --- Spin boxes for Vd and Vg ---
        self.vd_spin = QDoubleSpinBox()
        self.vd_spin.setRange(-10.0, 10.0)
        self.vd_spin.setSingleStep(0.1)
        self.vd_spin.setValue(self.k.Vd)
        self.vd_button = QPushButton("Set Vd")

        self.vg_spin = QDoubleSpinBox()
        self.vg_spin.setRange(-10.0, 10.0)
        self.vg_spin.setSingleStep(0.1)
        self.vg_spin.setValue(self.k.Vg)
        self.vg_button = QPushButton("Set Vg")

        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Vd:")); spin_layout.addWidget(self.vd_spin); spin_layout.addWidget(self.vd_button)
        spin_layout.addWidget(QLabel("Vg:")); spin_layout.addWidget(self.vg_spin); spin_layout.addWidget(self.vg_button)
        layout.addLayout(spin_layout)

        # --- Vg Pulse Button ---
        self.pulse_button = QPushButton("Start Vg Pulse")
        layout.addWidget(self.pulse_button)

        # --- Stop Button ---
        self.stop_button = QPushButton("Stop")
        layout.addWidget(self.stop_button)

        # --- Matplotlib Figure ---
        self.fig = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212, sharex=self.ax1)
        self.line_id, = self.ax1.plot([], [], 'b.-', label='I_Drain')
        self.line_ig, = self.ax2.plot([], [], 'r.-', label='I_Gate')
        self.ax1.set_ylabel('I_Drain'); self.ax2.set_ylabel('I_Gate'); self.ax2.set_xlabel('Time (s)')

        central.setLayout(layout)
        self.setCentralWidget(central)

        # --- Connect buttons ---
        self.vd_button.clicked.connect(self.set_vd)
        self.vg_button.clicked.connect(self.set_vg)
        self.pulse_button.clicked.connect(self.start_vg_pulse)
        self.stop_button.clicked.connect(self.stop_measurement)

        # --- Start measurement thread ---
        self.meas_worker.start()

        # --- Start plot timer ---
        self.timer = self.startTimer(200)  # 200 ms

    def set_vd(self):
        self.k.set_Vd(self.vd_spin.value())

    def set_vg(self):
        self.k.set_Vg(self.vg_spin.value())

    def stop_measurement(self):
        if self.meas_worker.is_alive():
            self.meas_worker.stop()
        if self.vg_pulse_worker and self.vg_pulse_worker.is_alive():
            self.vg_pulse_worker.stop()

    def timerEvent(self, event):
        # Update plot from worker data
        data = self.meas_worker.data
        if data:
            t_vals = [x[0] for x in data]
            i_d_vals = [x[2] for x in data]
            i_g_vals = [x[3] for x in data]
            self.line_id.set_data(t_vals, i_d_vals)
            self.line_ig.set_data(t_vals, i_g_vals)
            self.ax1.relim(); self.ax1.autoscale_view()
            self.ax2.relim(); self.ax2.autoscale_view()
            self.canvas.draw()

if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    app = QApplication(sys.argv)
    k = Keithley_2636B(RESOURCE_ID)
    k.connect()
    window = MainWindow(k)
    window.show()
    sys.exit(app.exec_())