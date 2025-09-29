from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from LabAuto.network import Connection
import sys

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

except KeyboardInterrupt:
    print("Exiting...")
finally:
    conn.sock.close()
