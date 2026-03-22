import sys
import serial
import serial.tools.list_ports
import time

class ServoController:
    def __init__(self, angle_on=90, angle_off=0):
        self.baudrate = 9600
        
        # --- ON/OFF ANGLE DEFINITIONS ---
        self.angle_on = angle_on
        self.angle_off = angle_off
        self.is_on = False  
        
        # --- SMART PORT DETECTION ---
        self.port = self.auto_detect_port()
        print(f"ServoController: Attempting to connect to: {self.port}")
        
        # Connect to the Arduino
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            
            # CRITICAL: Arduino reboots upon serial connection. Wait for it to wake up.
            time.sleep(2) 
            
            print("ServoController: Successfully connected to Arduino!")
            
            # Force the servo to the initial OFF position safely
            self.set_angle(self.angle_off)
            
        except serial.SerialException as e:
            # Raise an error so the main script knows the hardware failed to connect
            raise RuntimeError(f"Could not connect to Servo on {self.port}: {e}")

    def auto_detect_port(self):
        """Automatically scans USB ports for the Arduino CH340 chip."""
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            desc = port.description.lower()
            if "ch340" in desc or "arduino" in desc or "usb-serial" in desc or "usb serial" in desc:
                print(f"ServoController: Auto-detected Arduino at: {port.device} ({port.description})")
                return port.device
                
        print("ServoController: Could not auto-detect Arduino. Falling back to OS defaults...")
        if sys.platform.startswith('win'):
            return 'COM3' 
        elif sys.platform.startswith('darwin'):
            return '/dev/cu.usbserial-A5069RR4' 
        else:
            return '/dev/ttyUSB0' 

    def toggle_light(self):
        """Switches the state between ON and OFF angles."""
        if self.is_on:
            self.set_angle(self.angle_off)
            self.is_on = False
        else:
            self.set_angle(self.angle_on)
            self.is_on = True

    def set_angle(self, value):
        """Sends the exact integer angle to the Arduino."""
        if hasattr(self, 'ser') and self.ser.is_open:
            command = f"{value}\n"
            self.ser.write(command.encode('utf-8'))

    def close(self):
        """Safely shuts down the servo and closes the port."""
        if hasattr(self, 'ser') and self.ser.is_open:
            # Ensure the shutter is closed before walking away!
            self.set_angle(self.angle_off)
            time.sleep(0.5) # Give the motor time to physically move
            self.ser.close()
            print("ServoController: Connection closed safely.")

# --- Quick Test Block ---
# If you run `python servo.py` directly, it will just test the motor 3 times.
if __name__ == '__main__':
    print("Testing servo module independently...")
    try:
        servo = ServoController(angle_on=90, angle_off=50)
        for _ in range(3):
            servo.toggle_light()
            time.sleep(1)
        servo.close()
    except Exception as e:
        print(e)