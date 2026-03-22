import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QSlider, QLabel, QPushButton
from PyQt5.QtCore import Qt

class ServoGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.baudrate = 9600
        
        # --- ON/OFF ANGLE DEFINITIONS ---
        self.angle_on = 90  # Adjust this to the angle that turns the light ON
        self.angle_off = 70  # Adjust this to the resting/OFF angle
        self.is_on = False  
        
        # --- SMART PORT DETECTION ---
        self.port = self.auto_detect_port()
        print(f"Attempting to connect to: {self.port}")
        
        # Connect to the Arduino
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print("Successfully connected to Arduino!")
        except serial.SerialException as e:
            print(f"\nError opening port: {e}")
            print("Is the Arduino plugged in? Is the Arduino IDE Serial Monitor closed?")
            sys.exit(1)

        self.initUI()

    def auto_detect_port(self):
        """Automatically scans USB ports for the Arduino CH340 chip."""
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            desc = port.description.lower()
            # Look for common identifiers for clone and official Arduinos
            if "ch340" in desc or "arduino" in desc or "usb-serial" in desc or "usb serial" in desc:
                print(f"Auto-detected Arduino at: {port.device} ({port.description})")
                return port.device
                
        print("Could not auto-detect Arduino. Falling back to OS defaults...")
        # If the scan fails, guess based on the operating system
        if sys.platform.startswith('win'):
            return 'COM3' # Default Windows guess
        elif sys.platform.startswith('darwin'):
            return '/dev/cu.usbserial-A5069RR4' # Your specific Mac port
        else:
            return '/dev/ttyUSB0' # Linux guess

    def initUI(self):
        self.setWindowTitle('Servo Shutter Control')
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()

        # Label to display the current angle
        self.label = QLabel(f'Angle: {self.angle_off}°', self)
        self.label.setAlignment(Qt.AlignCenter)
        font = self.label.font()
        font.setPointSize(24)
        self.label.setFont(font)
        layout.addWidget(self.label)

        # TOGGLE BUTTON
        self.toggle_btn = QPushButton('Turn ON', self)
        self.toggle_btn.setMinimumHeight(50)
        self.toggle_btn.setStyleSheet("font-size: 18px; font-weight: bold; background-color: lightgreen;")
        self.toggle_btn.clicked.connect(self.toggle_light)
        layout.addWidget(self.toggle_btn)

        # Slider for manual calibration
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(180)
        self.slider.setValue(self.angle_off)
        self.slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.slider)

        self.setLayout(layout)

    def toggle_light(self):
        """Switches the state between ON and OFF angles."""
        if self.is_on:
            self.slider.setValue(self.angle_off) 
            self.toggle_btn.setText("Turn ON")
            self.toggle_btn.setStyleSheet("font-size: 18px; font-weight: bold; background-color: lightgreen;")
            self.is_on = False
        else:
            self.slider.setValue(self.angle_on) 
            self.toggle_btn.setText("Turn OFF")
            self.toggle_btn.setStyleSheet("font-size: 18px; font-weight: bold; background-color: lightcoral;")
            self.is_on = True

    def on_slider_change(self, value):
        self.label.setText(f'Angle: {value}°')
        
        command = f"{value}\n"
        self.ser.write(command.encode('utf-8'))

    def closeEvent(self, event):
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ServoGUI()
    ex.show()
    sys.exit(app.exec_())