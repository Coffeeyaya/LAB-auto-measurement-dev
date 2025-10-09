from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from LabAuto.network import Connection
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def celebrate_animation():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor('black')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # generate some random points for confetti
    n = 500
    x = np.random.rand(n)
    y = np.random.rand(n)
    colors = np.random.rand(n, 3)
    sizes = np.random.randint(20, 80, n)

    scat = ax.scatter(x, y, s=sizes, c=colors)

    def update(frame):
        # update positions randomly
        scat.set_offsets(np.c_[np.random.rand(n), np.random.rand(n)])
        return scat,

    ani = FuncAnimation(fig, update, frames=30, interval=150, blit=True, repeat=False)
    plt.show()

# iv computer (win 10)
SERVER_IP = "192.168.50.101"
PORT = 6000

class ParamDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter Measurement Parameters")
        self.resize(400, 250)
        self.params = {}

        layout = QVBoxLayout()

        # Input fields
        self.fields = {}
        for name in ["Material", "Device Number", "Measurement Type", "Measurement Index"]:
            hbox = QHBoxLayout()
            label = QLabel(name + ":")
            edit = QLineEdit()
            hbox.addWidget(label)
            hbox.addWidget(edit)
            layout.addLayout(hbox)
            self.fields[name] = edit

        # OK button
        btn = QPushButton("OK")
        btn.clicked.connect(self.on_ok)
        layout.addWidget(btn)

        self.setLayout(layout)

    def on_ok(self):
        for name, edit in self.fields.items():
            self.params[name.lower().replace(" ", "_")] = edit.text()
        self.accept()  # close dialog

def get_parameters():
    """Show the popup and return the entered parameters."""
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = ParamDialog()
    dialog.exec_()
    return dialog.params

# ------------------- Main -------------------
conn = Connection.connect(SERVER_IP, PORT)
print("[MAC] Connected to server")

try:
    while True:
        msg = conn.receive_json()
        cmd = msg.get("cmd")

        if cmd == "REQUEST_PARAMS":
            print(msg.get("message"))
            params = get_parameters()
            conn.send_json(params)

        elif cmd == "PROGRESS":
            print(f"[MAC] Progress update: {msg.get('progress')}")
            if msg.get('progress') == 'finished':
                celebrate_animation()


except KeyboardInterrupt:
    print("Exiting...")
finally:
    conn.sock.close()
