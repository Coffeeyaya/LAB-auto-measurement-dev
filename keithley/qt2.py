# qt_with_pulse.py
import sys
import time
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QDoubleSpinBox, QLabel, QLineEdit)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from keithley import Keithley2636B

# -------------------------------
# Worker Thread for Measurement
# -------------------------------
class KeithleyWorker(QThread):
    new_data = pyqtSignal(float, float, float, float, float)  # t, Vd, Vg, I_D, I_G

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


# -------------------------------
# PyQt5 GUI
# -------------------------------
class MainWindow(QWidget):
    def __init__(self, keithley, filename):
        super().__init__()
        self.setWindowTitle("Keithley Real-Time Control with Vg Pulse")
        self.k = keithley

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

        # Controls for Vd and Vg
        ctrl_layout = QHBoxLayout()
        layout.addLayout(ctrl_layout)

        self.Vd_spin = QDoubleSpinBox(); self.Vd_spin.setRange(-10,10); self.Vd_spin.setSingleStep(0.1); self.Vd_spin.setValue(self.k.Vd)
        self.Vg_spin = QDoubleSpinBox(); self.Vg_spin.setRange(-10,10); self.Vg_spin.setSingleStep(0.1); self.Vg_spin.setValue(self.k.Vg)
        self.set_Vd_btn = QPushButton("Set Vd"); self.set_Vg_btn = QPushButton("Set Vg")
        self.stop_btn = QPushButton("Stop")

        ctrl_layout.addWidget(QLabel("Vd:")); ctrl_layout.addWidget(self.Vd_spin); ctrl_layout.addWidget(self.set_Vd_btn)
        ctrl_layout.addWidget(QLabel("Vg:")); ctrl_layout.addWidget(self.Vg_spin); ctrl_layout.addWidget(self.set_Vg_btn)
        ctrl_layout.addWidget(self.stop_btn)

        # Pulse controls
        pulse_layout = QHBoxLayout()
        layout.addLayout(pulse_layout)
        self.pulse_input = QLineEdit("1.0,5.0;-1.0,5.0")  # default Vg,duration pairs
        self.start_pulse_btn = QPushButton("Start Pulse")
        self.stop_pulse_btn = QPushButton("Stop Pulse")
        pulse_layout.addWidget(QLabel("Vg Pulse Seq (V,duration;s...):"))
        pulse_layout.addWidget(self.pulse_input)
        pulse_layout.addWidget(self.start_pulse_btn)
        pulse_layout.addWidget(self.stop_pulse_btn)

        # Connect signals
        self.set_Vd_btn.clicked.connect(self.apply_Vd)
        self.set_Vg_btn.clicked.connect(self.apply_Vg)
        self.stop_btn.clicked.connect(self.stop)
        self.start_pulse_btn.clicked.connect(self.start_pulse)
        self.stop_pulse_btn.clicked.connect(self.stop_pulse)

        # Data storage
        self.times, self.I_Ds, self.I_Gs = [], [], []

        # CSV file
        self.csv_file = filename
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time","Vd","Vg","I_D","I_G"])

        # Start worker thread
        self.worker = KeithleyWorker(self.k)
        self.worker.new_data.connect(self.update_plot)
        self.worker.start()

    # Apply Set button values
    def apply_Vd(self):
        value = self.Vd_spin.value()
        self.k.set_Vd(value)
        print(f"Vd set to {value} V")

    def apply_Vg(self):
        value = self.Vg_spin.value()
        self.k.set_Vg(value)
        print(f"Vg set to {value} V")

    # Pulse control
    def start_pulse(self):
        try:
            seq_text = self.pulse_input.text()
            seq = []
            for item in seq_text.split(";"):
                v,d = item.split(",")
                seq.append( (float(v), float(d)) )
            self.k.start_vg_pulse(seq)
        except Exception as e:
            print("Invalid pulse sequence:", e)

    def stop_pulse(self):
        self.k.stop_vg_pulse()

    # Update plot and CSV
    def update_plot(self, t, Vd, Vg, I_D, I_G):
        self.times.append(t)
        self.I_Ds.append(I_D)
        self.I_Gs.append(I_G)
        self.line_id.set_data(self.times, self.I_Ds)
        self.line_ig.set_data(self.times, self.I_Gs)
        self.ax1.relim(); self.ax1.autoscale_view()
        self.ax2.relim(); self.ax2.autoscale_view()
        self.canvas.draw()

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t,Vd,Vg,I_D,I_G])

    # Stop everything
    def stop(self):
        self.worker.stop()
        self.k.stop_vg_pulse()
        self.k.set_Vd(0)
        self.k.set_Vg(0)
        self.k.shutdown()
        # disable controls
        self.set_Vd_btn.setEnabled(False)
        self.set_Vg_btn.setEnabled(False)
        self.Vd_spin.setEnabled(False)
        self.Vg_spin.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_pulse_btn.setEnabled(False)
        self.stop_pulse_btn.setEnabled(False)


if __name__ == "__main__":
    RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
    filename = "qt_pulse.csv"
    keithley = Keithley2636B(RESOURCE_ID)
    keithley.connect()
    keithley.clean_instrument()
    keithley.config()

    app = QApplication(sys.argv)
    window = MainWindow(keithley, filename)
    window.show()
    sys.exit(app.exec_())
