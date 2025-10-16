import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation

class ConfettiCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(6, 4))
        super().__init__(fig)
        self.setParent(parent)
        self.ax = self.figure.subplots()
        self.ax.set_facecolor('black')
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')

        n = 300
        self.x = np.random.rand(n)
        self.y = np.random.rand(n)
        self.colors = np.random.rand(n, 3)
        self.sizes = np.random.randint(20, 80, n)
        self.scat = self.ax.scatter(self.x, self.y, s=self.sizes, c=self.colors)

        self.ani = FuncAnimation(self.figure, self.update, frames=30, interval=150, blit=True, repeat=False)

    def update(self, frame):
        self.scat.set_offsets(np.c_[np.random.rand(len(self.x)), np.random.rand(len(self.y))])
        return self.scat,

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Embedded Confetti Demo")
        self.canvas = ConfettiCanvas(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.resize(600, 400)

app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
