import sys
import time
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pyvisa
from keithley import Keithley2636B


# --- Worker Thread ---
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
            self.new_data.emit(t, self.k.Vd, self.k.Vg, I_D, I_G)
            self.msleep(100)  # 10 Hz

    def stop(self):
        self.running = False
        self.wait()


# --- PyQt5 GUI ---
class MainWindow(QWidget):
    def __init__(self, keithley):
        super().__init__()
        self.setWindowTitle("Keithley Real-Time Control")
        self.k = keithley

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Matplotlib Figure
        self.figure = Figure(figsize=(6,4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        self.line_id, = self.ax1.plot([], [], 'b.-', label='I_D')
        self.line_ig, = self.ax2.plot([], [], 'r.-', label='I_G')
        self.ax1.set_ylabel("I_D (A)")
        self.ax2.set_ylabel("I_G (A)")
        self.ax2.set_xlabel("Time (s)")
        self.ax1.legend(); self.ax2.legend()

        # SpinBoxes for Vd and Vg
        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        self.Vd_spin = QDoubleSpinBox()
        self.Vd_spin.setRange(-10.0, 10.0)
        self.Vd_spin.setSingleStep(0.1)
        self.Vd_spin.setValue(self.k.Vd)

        self.Vg_spin = QDoubleSpinBox()
        self.Vg_spin.setRange(-10.0, 10.0)
        self.Vg_spin.setSingleStep(0.1)
        self.Vg_spin.setValue(self.k.Vg)

        self.up_Vd = QPushButton("Vd +0.1")
        self.down_Vd = QPushButton("Vd -0.1")
        self.up_Vg = QPushButton("Vg +0.1")
        self.down_Vg = QPushButton("Vg -0.1")
        self.stop_btn = QPushButton("Stop")

        ctrl_layout.addWidget(QLabel("Vd:"))
        ctrl_layout.addWidget(self.Vd_spin)
        ctrl_layout.addWidget(self.up_Vd)
        ctrl_layout.addWidget(self.down_Vd)
        ctrl_layout.addWidget(QLabel("Vg:"))
        ctrl_layout.addWidget(self.Vg_spin)
        ctrl_layout.addWidget(self.up_Vg)
        ctrl_layout.addWidget(self.down_Vg)
        ctrl_layout.addWidget(self.stop_btn)

        # Connect signals
        self.Vd_spin.valueChanged.connect(self.k.set_Vd)
        self.Vg_spin.valueChanged.connect(self.k.set_Vg)
        self.up_Vd.clicked.connect(lambda: self.Vd_spin.setValue(self.Vd_spin.value()+0.1))
        self.down_Vd.clicked.connect(lambda: self.Vd_spin.setValue(self.Vd_spin.value()-0.1))
        self.up_Vg.clicked.connect(lambda: self.Vg_spin.setValue(self.Vg_spin.value()+0.1))
        self.down_Vg.clicked.connect(lambda: self.Vg_spin.setValue(self.Vg_spin.value()-0.1))
        self.stop_btn.clicked.connect(self.stop)

        # Data storage
        self.times, self.I_Ds, self.I_Gs = [], [], []

        # CSV file
        self.csv_file = "real_time_data.csv"
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time","Vd","Vg","I_D","I_G"])

        # Start worker
        self.worker = KeithleyWorker(self.k)
        self.worker.new_data.connect(self.update_plot)
        self.worker.start()

    def update_plot(self, t, Vd, Vg, I_D, I_G):
        self.times.append(t)
        self.I_Ds.append(I_D)
        self.I_Gs.append(I_G)

        # Update plot
        self.line_id.set_data(self.times, self.I_Ds)
        self.line_ig.set_data(self.times, self.I_Gs)
        self.ax1.relim(); self.ax1.autoscale_view()
        self.ax2.relim(); self.ax2.autoscale_view()
        self.canvas.draw()

        # Save CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t, Vd, Vg, I_D, I_G])

    def stop(self):
        self.worker.stop()
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.shutdown()
        self.close()


# --- Run App ---
if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    keithley = Keithley2636B(RESOURCE_ID)
    keithley.connect()
    keithley.clean_instrument()
    keithley.config()

    app = QApplication(sys.argv)
    win = MainWindow(keithley)
    win.show()
    sys.exit(app.exec_())
