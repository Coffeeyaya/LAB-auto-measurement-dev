import sys
import time
import random
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QHBoxLayout)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------------------
# Worker Thread
# ---------------------------
class MeasurementWorker(QThread):
    new_data = pyqtSignal(float, float, float)  # t, voltage, current

    def __init__(self):
        super().__init__()
        self.voltage = 0.0
        self.running = True

    def run(self):
        start_time = time.time()
        while self.running:
            current = self.voltage * 0.1 + random.uniform(-0.01, 0.01)
            t = time.time() - start_time
            self.new_data.emit(t, self.voltage, current)
            self.msleep(500)

    def set_voltage(self, v):
        self.voltage = v

    def stop(self):
        self.running = False
        self.wait()


# ---------------------------
# Main GUI
# ---------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Threaded Measurement with PyQt5")

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Plot
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], 'b.-')
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.ax.grid(True)

        # Voltage controls
        self.label = QLabel("Voltage: 0.0 V")
        layout.addWidget(self.label)

        hlayout = QHBoxLayout()
        self.up_btn = QPushButton("+0.5V")
        self.down_btn = QPushButton("-0.5V")
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type voltage and press Enter")
        hlayout.addWidget(self.up_btn)
        hlayout.addWidget(self.down_btn)
        hlayout.addWidget(self.input_line)
        layout.addLayout(hlayout)

        self.stop_btn = QPushButton("Stop")
        layout.addWidget(self.stop_btn)

        # Data storage for CSV
        self.times = []
        self.currents = []
        self.voltages = []

        # Voltage value
        self.voltage = 0.0

        # Worker thread
        self.worker = MeasurementWorker()
        self.worker.new_data.connect(self.update_plot)
        self.worker.start()

        # Connect buttons and input
        self.up_btn.clicked.connect(self.increase_voltage)
        self.down_btn.clicked.connect(self.decrease_voltage)
        self.input_line.returnPressed.connect(self.set_voltage_from_input)
        self.stop_btn.clicked.connect(self.stop_measurement)

        # CSV filename
        self.filename = "measurement_data.csv"
        # write header
        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "Voltage", "Current"])

    # ---------------------------
    # Slot: update plot and save CSV
    # ---------------------------
    def update_plot(self, t, v, i):
        self.times.append(t)
        self.currents.append(i)
        self.voltages.append(v)

        # update line
        self.line.set_data(self.times, self.currents)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        # update label
        self.label.setText(f"Voltage: {v:.2f} V")

        # save to CSV
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([t, v, i])

    # ---------------------------
    # Button actions
    # ---------------------------
    def increase_voltage(self):
        self.voltage += 0.5
        self.worker.set_voltage(self.voltage)

    def decrease_voltage(self):
        self.voltage -= 0.5
        self.worker.set_voltage(self.voltage)

    def set_voltage_from_input(self):
        text = self.input_line.text()
        try:
            v = float(text)
            self.voltage = v
            self.worker.set_voltage(self.voltage)
            self.input_line.clear()
        except ValueError:
            self.input_line.clear()  # invalid input

    def stop_measurement(self):
        self.worker.stop()
        self.close()


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
