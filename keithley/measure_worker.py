import sys
import time
import csv
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton
from keithley2636b import Keithley2636B  # your Keithley class

FILENAME = "shared_data.csv"
MEASURE_INTERVAL = 0.1  # seconds

# -------------------------------
# QThread for continuous measurement
# -------------------------------
class MeasureThread(QThread):
    new_data = pyqtSignal(float, float, float, float, float)  # time, Vd, Vg, Id, Ig

    def __init__(self, keithley: Keithley2636B):
        super().__init__()
        self.k = keithley
        self.running = True

    def run(self):
        start_time = time.time()
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Drain", "V_Gate", "I_Drain", "I_Gate"])
            while self.running:
                with self.k.lock:
                    Vd = self.k.Vd
                    Vg = self.k.Vg
                Id, Ig = self.k.measure()
                t = time.time() - start_time
                writer.writerow([t, Vd, Vg, Id, Ig])
                f.flush()
                self.new_data.emit(t, Vd, Vg, Id, Ig)
                time.sleep(MEASURE_INTERVAL)

    def stop(self):
        self.running = False


# -------------------------------
# QThread for Vg pulses
# -------------------------------
class PulseThread(QThread):
    def __init__(self, keithley: Keithley2636B, pulse_sequence: list):
        super().__init__()
        self.k = keithley
        self.pulse_sequence = pulse_sequence
        self.running = True

    def run(self):
        while self.running:
            for Vg, duration in self.pulse_sequence:
                if not self.running:
                    break
                self.k.set_Vg(Vg)
                t_end = time.time() + duration
                while time.time() < t_end:
                    if not self.running:
                        break
                    time.sleep(0.01)

    def stop(self):
        self.running = False


# -------------------------------
# PyQt GUI
# -------------------------------
class KeithleyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley 2636B Controller")

        # Keithley instance
        RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
        self.k = Keithley2636B(RESOURCE_ID)
        self.k.connect()
        self.k.clean_instrument()
        self.k.config()
        self.k.set_Vd(1.0)
        self.k.set_Vg(0.0)

        # Threads
        self.measure_thread = MeasureThread(self.k)
        self.pulse_thread = None

        # UI Elements
        layout = QVBoxLayout()

        # Drain voltage control
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Vd (Drain)"))
        self.spin_vd = QDoubleSpinBox()
        self.spin_vd.setRange(0, 10)
        self.spin_vd.setValue(self.k.Vd)
        self.spin_vd.setSingleStep(0.1)
        h1.addWidget(self.spin_vd)
        self.btn_set_vd = QPushButton("Set Vd")
        h1.addWidget(self.btn_set_vd)
        layout.addLayout(h1)

        # Gate voltage control
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Vg (Gate)"))
        self.spin_vg = QDoubleSpinBox()
        self.spin_vg.setRange(-10, 10)
        self.spin_vg.setValue(self.k.Vg)
        self.spin_vg.setSingleStep(0.1)
        h2.addWidget(self.spin_vg)
        self.btn_set_vg = QPushButton("Set Vg")
        h2.addWidget(self.btn_set_vg)
        layout.addLayout(h2)

        # Start / Stop buttons
        h3 = QHBoxLayout()
        self.btn_start = QPushButton("Start Measurement")
        self.btn_stop = QPushButton("Stop Measurement")
        h3.addWidget(self.btn_start)
        h3.addWidget(self.btn_stop)
        layout.addLayout(h3)

        self.setLayout(layout)

        # Connect buttons
        self.btn_set_vd.clicked.connect(self.set_vd)
        self.btn_set_vg.clicked.connect(self.set_vg)
        self.btn_start.clicked.connect(self.start_measurement)
        self.btn_stop.clicked.connect(self.stop_measurement)

    def set_vd(self):
        val = self.spin_vd.value()
        self.k.set_Vd(val)

    def set_vg(self):
        val = self.spin_vg.value()
        self.k.set_Vg(val)

    def start_measurement(self):
        if not self.measure_thread.isRunning():
            self.measure_thread.start()
        # Example pulse sequence: alternate +1/-1 V every 1 s
        if self.pulse_thread is None:
            pulse_sequence = [(1.0, 1.0), (-1.0, 1.0)]
            self.pulse_thread = PulseThread(self.k, pulse_sequence)
            self.pulse_thread.start()

    def stop_measurement(self):
        self.measure_thread.stop()
        if self.pulse_thread is not None:
            self.pulse_thread.stop()
        self.k.set_Vd(0.0)
        self.k.set_Vg(0.0)

    def closeEvent(self, event):
        # Ensure threads are stopped
        self.stop_measurement()
        self.k.shutdown()
        event.accept()


# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = KeithleyGUI()
    gui.show()
    sys.exit(app.exec_())
