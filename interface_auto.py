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


def celebrate_animation():
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
    """
    Connect to iv_run server, ensuring old connections/threads are cleaned.
    """
    try:
        # Connect new socket
        self.conn = Connection.connect(self.server_ip, self.server_port)
        self.append_log(f"Connected to {self.server_ip}:{self.server_port}")

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
