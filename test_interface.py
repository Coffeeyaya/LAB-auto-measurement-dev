import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtGui import QFont
import sys
import os

class LabControlUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lab Auto Measurement Control")
        self.resize(500, 200)

        font_button = QFont("Arial", 14)

        layout = QVBoxLayout()

        # ---------- Buttons for clients ----------
        button_names = {
            "Win7 Client": "client_win7.py",
            "Win10 Client": "client_win10.py",
            "IV Client": "client_iv.py",
            "CSV Client": "client_csv.py"
        }

        for display_name, script_name in button_names.items():
            btn = QPushButton(display_name)
            btn.setFont(font_button)
            btn.clicked.connect(lambda checked, s=script_name: self.launch_client_in_new_terminal(s))
            layout.addWidget(btn)

        self.setLayout(layout)

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
