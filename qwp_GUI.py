import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from kCube import WaveplateController

class QWPGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- PREDEFINED ANGLES ---
        self.angle_rcp = 45
        self.angle_lcp = 135
        
        self.qwp = None
        
        # Connect to the Motor
        try:
            self.qwp = WaveplateController()
            print("Successfully connected to QWP Motor!")
        except Exception as e:
            # We don't sys.exit here so the window still shows an error message
            print(f"Connection Error: {e}")

        self.initUI()
        
        # Timer to periodically update the current angle display
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_angle_display)
        self.timer.start(500) # Update every 500ms

    def initUI(self):
        self.setWindowTitle('QWP Manual Control')
        self.setGeometry(300, 300, 400, 300)

        layout = QVBoxLayout()

        # --- CURRENT ANGLE DISPLAY ---
        self.label_status = QLabel('Current Angle: --°', self)
        self.label_status.setAlignment(Qt.AlignCenter)
        font = self.label_status.font()
        font.setPointSize(20)
        font.setBold(True)
        self.label_status.setFont(font)
        layout.addWidget(self.label_status)
        
        if self.qwp is None:
            err_label = QLabel('⚠️ MOTOR NOT FOUND', self)
            err_label.setStyleSheet("color: red; font-weight: bold;")
            err_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(err_label)

        layout.addSpacing(20)

        # --- QUICK ACCESS BUTTONS ---
        h_layout_quick = QHBoxLayout()
        
        self.btn_rcp = QPushButton('RCP (45°)', self)
        self.btn_rcp.setMinimumHeight(60)
        self.btn_rcp.setStyleSheet("font-size: 16px; background-color: #e1f5fe;")
        self.btn_rcp.clicked.connect(lambda: self.move_to(self.angle_rcp))
        h_layout_quick.addWidget(self.btn_rcp)
        
        self.btn_lcp = QPushButton('LCP (135°)', self)
        self.btn_lcp.setMinimumHeight(60)
        self.btn_lcp.setStyleSheet("font-size: 16px; background-color: #fce4ec;")
        self.btn_lcp.clicked.connect(lambda: self.move_to(self.angle_lcp))
        h_layout_quick.addWidget(self.btn_lcp)
        
        layout.addLayout(h_layout_quick)
        
        layout.addSpacing(20)

        # --- MANUAL INPUT ---
        h_layout_manual = QHBoxLayout()
        self.input_angle = QLineEdit(self)
        self.input_angle.setPlaceholderText("Enter angle (0-360)")
        self.input_angle.setMinimumHeight(40)
        h_layout_manual.addWidget(self.input_angle)
        
        self.btn_move = QPushButton('Rotate', self)
        self.btn_move.setMinimumHeight(40)
        self.btn_move.clicked.connect(self.manual_move)
        h_layout_manual.addWidget(self.btn_move)
        
        layout.addLayout(h_layout_manual)

        layout.addSpacing(20)

        # --- UTILITY BUTTONS ---
        h_layout_utils = QHBoxLayout()
        
        self.btn_home = QPushButton('🏠 Home Motor', self)
        self.btn_home.setMinimumHeight(40)
        self.btn_home.setStyleSheet("background-color: #eeeeee;")
        self.btn_home.clicked.connect(self.home_motor)
        h_layout_utils.addWidget(self.btn_home)
        
        layout.addLayout(h_layout_utils)

        self.setLayout(layout)

    def update_angle_display(self):
        if self.qwp:
            try:
                angle = self.qwp.get_current_angle()
                self.label_status.setText(f'Current Angle: {angle:.2f}°')
            except:
                self.label_status.setText('Current Angle: ERROR')

    def move_to(self, angle):
        if self.qwp:
            try:
                # Use non-blocking move for GUI responsiveness
                self.qwp.move_to_degree(angle, wait=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Movement failed: {e}")

    def manual_move(self):
        text = self.input_angle.text()
        try:
            angle = float(text)
            self.move_to(angle)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric angle.")

    def home_motor(self):
        if self.qwp:
            reply = QMessageBox.question(self, 'Homing', 'Start homing procedure? (Motor will rotate to physical zero)',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    self.qwp.home(wait=False)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Homing failed: {e}")

    def closeEvent(self, event):
        if self.qwp:
            self.qwp.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = QWPGUI()
    ex.show()
    sys.exit(app.exec_())
