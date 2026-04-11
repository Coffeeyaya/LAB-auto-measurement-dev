import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class BaseMeasurementWindow(QWidget):
    def __init__(self, worker, window_title="Measurement Dashboard"):
        super().__init__()
        self.setWindowTitle(window_title)
        self.worker = worker
        
        self.data_memory = {}
        self.lines_dict = {} 
        self.last_draw_time = time.time()

        self._setup_base_ui()
        self._setup_custom_axes() 
        
        self.worker.status_update.connect(self.update_status)
        self.worker.sequence_finished.connect(self.on_finished)
        
        self.worker.start()

    def _setup_base_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.status_label = QLabel("Status: Starting up...")
        self.status_label.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def update_status(self, text):
        self.status_label.setText(text)
        self.worker.status_label_text = text

    def on_finished(self):
        # Final redraw to ensure all axes are scaled properly
        if hasattr(self, 'ax1') and self.ax1.get_autoscale_on():
            self.ax1.relim()
            self.ax1.autoscale_view()
        self.canvas.draw()
        
        if "FILE EXISTS ERROR" not in self.status_label.text():
            self.status_label.setText("Status: Batch Sequence Finished. Hardware is safe.")
        
    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.stop()
        event.accept()

    def _setup_custom_axes(self):
        raise NotImplementedError("Child must define _setup_custom_axes()!")
    
class TimeDepWindow(BaseMeasurementWindow):
    def __init__(self, worker):
        super().__init__(worker, window_title="Time-Dependent Measurement")
        
        self.lines_id = {}
        self.lines_ig = {}
        self.lines_vd = {}
        self.lines_vg = {}

        self.worker.new_config.connect(self.add_config_line)
        self.worker.new_data.connect(self.update_plot)

    def _setup_custom_axes(self):
        """Creates the 2-panel layout."""
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
        
        self.ax1.set_ylabel("Id (A)", color='blue')
        self.ax2.set_ylabel("Ig (A)", color='red')
        self.ax2.set_xlabel("Time (s)")
        
        self.ax1_v = self.ax1.twinx()
        self.ax2_v = self.ax2.twinx()
        self.ax1_v.set_ylabel("Vd (V)", color='green')
        self.ax2_v.set_ylabel("Vg Target (V)", color='black')

    def add_config_line(self, config_idx, label):
        self.data_memory[config_idx] = {"t": [], "id": [], "ig": [], "vd": [], "vg": []}
        
        self.lines_id[config_idx], = self.ax1.plot([], [], '.-', label=f'Id ({label})')
        self.lines_ig[config_idx], = self.ax2.plot([], [], '.-', label=f'Ig ({label})')
        self.lines_vd[config_idx], = self.ax1_v.plot([], [], '', alpha=0.3)
        self.lines_vg[config_idx], = self.ax2_v.plot([], [], '', alpha=0.3)
        
        self.ax1.legend(loc='best')
        self.ax2.legend(loc='best')
        self.canvas.draw()

    def update_plot(self, config_idx, data):
        """Unpacks the DataClass directly."""
        mem = self.data_memory[config_idx]
        mem["t"].append(data.Time)
        mem["vd"].append(data.Vd)
        mem["vg"].append(data.Vg)
        mem["id"].append(data.Id)
        mem["ig"].append(data.Ig)
        
        self.lines_id[config_idx].set_data(mem["t"], mem["id"])
        self.lines_ig[config_idx].set_data(mem["t"], mem["ig"])
        self.lines_vd[config_idx].set_data(mem["t"], mem["vd"])
        self.lines_vg[config_idx].set_data(mem["t"], mem["vg"])
        
        current_time = time.time()
        if current_time - self.last_draw_time > 0.2:
            for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
                if ax.get_autoscale_on():
                    ax.relim()
                    ax.autoscale_view()
            self.canvas.draw()
            self.last_draw_time = current_time

    def on_finished(self):
        """Override the parent to ensure all 4 axes are rescaled at the end."""
        for ax in [self.ax1, self.ax2, self.ax1_v, self.ax2_v]:
            if ax.get_autoscale_on():
                ax.relim()
                ax.autoscale_view()
        super().on_finished() # Call the parent to update the status label
