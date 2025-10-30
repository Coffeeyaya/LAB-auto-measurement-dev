import sys
from PyQt5 import QtCore
import os
import threading
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox, QGroupBox
)
from PyQt5.QtGui import QFont
from LabAuto.network import Connection  # same Connection used by iv_run
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation


def launch_script(script_name):
    # If running as .exe, scripts are inside sys._MEIPASS
    if getattr(sys, 'frozen', False):
        script_path = os.path.join(sys._MEIPASS, script_name)
    else:
        script_path = script_name

    subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)


class LabControlUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lab Auto Measurement Control")
        self.resize(700, 500)

        self.conn = None
        self.listener_thread = None
        self.listening = False

        font_button = QFont("Arial", 20)
        app.setFont(font_button)
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
        laser_layout = QVBoxLayout()
        time_layout = QVBoxLayout()

        params_layout.addLayout(left_layout)
        params_layout.addLayout(right_layout)
        params_layout.addLayout(laser_layout)
        params_layout.addLayout(time_layout)

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

        laser_layout.addWidget(QLabel("laser functions:"))
        self.laser_function_combo = QComboBox()
        self.laser_function_combo.addItems(["1_on_off", "wavelength", "power"])
        laser_layout.addWidget(self.laser_function_combo)

        time_layout.addWidget(QLabel("rest time:"))
        self.rest_time = QLineEdit()
        time_layout.addWidget(self.rest_time)

        time_layout.addWidget(QLabel("dark time1:"))
        self.dark_time1 = QLineEdit()
        time_layout.addWidget(self.dark_time1)

        time_layout.addWidget(QLabel("dark time2:"))
        self.dark_time2 = QLineEdit()
        time_layout.addWidget(self.dark_time2)

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

    def celebrate_animation(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_facecolor('black')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        n = 500
        x = np.random.rand(n)
        y = np.random.rand(n)
        colors = np.random.rand(n, 3)
        sizes = np.random.randint(20, 80, n)
        scat = ax.scatter(x, y, s=sizes, c=colors)

        def update(frame):
            scat.set_offsets(np.c_[np.random.rand(n), np.random.rand(n)])
            return scat,

        ani = FuncAnimation(fig, update, frames=30, interval=150, blit=True, repeat=False)

        plt.show(block=False)
        plt.pause(5)  # <-- let it run for 5 seconds before window closes
        plt.close()

    # ----------------- Connection + Send -----------------
    def connect_to_server(self):
        """Connect to iv_run server, ensuring old connections/threads are cleaned."""
        try:
            # Stop old listener thread
            self.listening = False
            if hasattr(self, "listener_thread") and self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=0.1)

            # Close old socket
            if hasattr(self, "conn") and self.conn:
                try:
                    self.conn.sock.close()
                except:
                    pass
                self.conn = None

            # Connect new socket
            self.conn = Connection.connect(self.server_ip, self.server_port)
            self.append_log(f"Connected to {self.server_ip}:{self.server_port}")

            # Start fresh listener thread
            self.listening = True
            self.listener_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.listener_thread.start()
            return True
        except Exception as e:
            self.append_log(f"Connection failed: {e}")
            self.conn = None
            return False


    def send_params_and_listen(self):
        params = self.collect_params()

        try:
            # Ensure connection
            if not self.conn:
                self.connect_to_server()
            self.conn.send_json(params)
            self.append_log(f"Sent parameters: {params}")

        except Exception as e:
            self.append_log(f"Error sending parameters: {e}")
            self.append_log("Attempting to reconnect and resend...")

            # Close old socket if broken
            if self.conn:
                try:
                    self.conn.sock.close()
                except:
                    pass
                self.conn = None
                self.listening = False

            # Reconnect and resend
            if self.connect_to_server():
                try:
                    self.conn.send_json(params)
                    self.append_log(f"Sent parameters: {params}")
                except Exception as e2:
                    self.append_log(f"Failed again: {e2}")


    def listen_to_server(self):
        self.append_log("Listening for server messages...")
        while self.listening and self.conn:
            try:
                msg = self.conn.receive_json()
                if not msg:
                    break
                cmd = msg.get("cmd", "")
                if cmd == "PROGRESS":
                    self.append_log(f"Progress: {msg.get('progress')}")
                    if msg.get('progress') == 'finished':
                        # print('hi')
                        # run celebrate_animation in main thread safely
                        QtCore.QTimer.singleShot(0, self.celebrate_animation)
                elif cmd == "REQUEST_PARAMS":
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
            "measurement_index": str(self.measurement_index_spin.value()),
            "laser_function": self.laser_function_combo.currentText(),
            "rest_time": self.rest_time.text().strip(),
            "dark_time1": self.dark_time1.text().strip(),
            "dark_time2": self.dark_time2.text().strip()
        }

    def append_log(self, text):
        self.log.append(text)
        self.log.moveCursor(self.log.textCursor().End)

    def launch_client_in_new_terminal(self, script_name):
        # Determine script path depending on whether running as exe or normal
        # if getattr(sys, 'frozen', False):
        #     # Running as PyInstaller exe
        #     script_path = os.path.join(sys._MEIPASS, script_name)
        # else:
        script_path = os.path.abspath(script_name)

        python_executable = sys.executable

        if sys.platform == "darwin":  # macOS
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
            subprocess.Popen(
                ["cmd.exe", "/k", python_executable, script_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

        else:  # Linux
            subprocess.Popen(
                ["gnome-terminal", "--", python_executable, script_path]
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LabControlUI()
    window.show()
    sys.exit(app.exec_())
