import sys
import os
import threading
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox, QGroupBox
)
from PyQt5.QtGui import QFont
from LabAuto.network import Connection  # same Connection used by iv_run


class LabControlUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lab Auto Measurement Control")
        self.resize(700, 500)

        self.conn = None
        self.listener_thread = None
        self.listening = False

        font_button = QFont("Arial", 12)
        main_layout = QVBoxLayout()

        # --- Fixed connection info ---
        self.server_ip = "192.168.50.101"
        self.server_port = 6000

        # --- Parameter Section ---
        params_group = QGroupBox("Measurement Parameters")
        params_layout = QHBoxLayout()
        params_group.setLayout(params_layout)

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        params_layout.addLayout(left_layout)
        params_layout.addLayout(right_layout)

        left_layout.addWidget(QLabel("Material:"))
        self.material_edit = QLineEdit()
        left_layout.addWidget(self.material_edit)

        left_layout.addWidget(QLabel("Device Number:"))
        self.device_number_edit = QLineEdit()
        left_layout.addWidget(self.device_number_edit)

        left_layout.addWidget(QLabel("Measurement Index:"))
        self.measurement_index_spin = QSpinBox()
        self.measurement_index_spin.setMinimum(0)
        self.measurement_index_spin.setMaximum(9999)
        left_layout.addWidget(self.measurement_index_spin)

        right_layout.addWidget(QLabel("Measurement Type:"))
        self.measurement_type_combo = QComboBox()
        self.measurement_type_combo.addItems(["idvg", "idvd", "time"])
        right_layout.addWidget(self.measurement_type_combo)

        self.send_btn = QPushButton("Send Parameters and Run")
        self.send_btn.setFont(font_button)
        self.send_btn.clicked.connect(self.send_params_and_listen)
        params_layout.addWidget(self.send_btn)

        main_layout.addWidget(params_group)

        # --- Progress / Log ---
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_layout.addWidget(QLabel("Progress Log:"))
        main_layout.addWidget(self.log)

        # --- Launch Buttons (for other scripts) ---
        clients_group = QGroupBox("Other Clients")
        clients_layout = QVBoxLayout()
        clients_group.setLayout(clients_layout)
        main_layout.addWidget(clients_group)

        button_names = {
            "Win7 Client": "client_win7.py",
            "Win10 Client": "client_win10.py",
            "CSV Client": "client_csv.py"
        }

        for display_name, script_name in button_names.items():
            btn = QPushButton(display_name)
            btn.setFont(font_button)
            btn.clicked.connect(lambda checked, s=script_name: self.launch_client_in_new_terminal(s))
            clients_layout.addWidget(btn)

        self.setLayout(main_layout)

    # ----------------- Connection + Send -----------------
    def connect_to_server(self):
        """Connect to iv_run server if not already connected."""
        if self.conn is not None:
            return True
        try:
            self.append_log(f"Connecting to {self.server_ip}:{self.server_port} ...")
            self.conn = Connection.connect(self.server_ip, self.server_port)
            self.append_log("Connected.")
            self.listening = True
            self.listener_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.listener_thread.start()
            return True
        except Exception as e:
            self.append_log(f"Connection failed: {e}")
            self.conn = None
            return False

    def send_params_and_listen(self):
        """Called when the Send button is clicked."""
        if not self.connect_to_server():
            return
        try:
            params = self.collect_params()
            self.conn.send_json(params)
            self.append_log(f"Sent parameters: {params}")
        except Exception as e:
            self.append_log(f"Error sending parameters: {e}")

    def listen_to_server(self):
        """Background thread: listens for messages from iv_run."""
        self.append_log("Listening for server messages...")
        while self.listening and self.conn:
            try:
                msg = self.conn.receive_json()
                if not msg:
                    break
                cmd = msg.get("cmd", "")
                if cmd == "PROGRESS":
                    self.append_log(f"Progress: {msg.get('progress')}")
                elif cmd == "REQUEST_PARAMS":
                    # If iv_run asks explicitly, send again
                    self.append_log("Server requested parameters again.")
                    self.conn.send_json(self.collect_params())
                else:
                    self.append_log(f"Received: {msg}")
            except Exception as e:
                self.append_log(f"Listener error: {e}")
                break
        self.append_log("Listener stopped.")

    # ----------------- Utility -----------------
    def collect_params(self):
        return {
            "material": self.material_edit.text().strip(),
            "device_number": self.device_number_edit.text().strip(),
            "measurement_type": self.measurement_type_combo.currentText(),
            "measurement_index": str(self.measurement_index_spin.value())
        }

    def append_log(self, text):
        self.log.append(text)
        self.log.moveCursor(self.log.textCursor().End)


    def launch_client_in_new_terminal(self, script_name):
        python_executable = sys.executable
        script_path = os.path.abspath(script_name)

        if sys.platform == "darwin":  # macOS
            # Launch in iTerm
            applescript = f'''
            tell application "iTerm"
                create window with default profile
                tell current window
                    tell current session
                        write text "{python_executable} {script_path}"
                    end tell
                end tell
            end tell
            '''
            subprocess.Popen(
                ["osascript", "-e", applescript],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        elif sys.platform == "win32":
            # Launch in new Windows console
            subprocess.Popen(
                [python_executable, script_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

        else:  # Linux
            # Launch in new gnome-terminal window
            subprocess.Popen(
                ["gnome-terminal", "--", python_executable, script_path]
            )



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LabControlUI()
    window.show()
    sys.exit(app.exec_())
