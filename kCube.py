from pylablib.devices import Thorlabs
import time

class WaveplateController:
    """
    A wrapper class for Thorlabs Kinesis Rotation Mounts (e.g., PRM1Z8 / K10CR1).
    """
    
    def __init__(self, serial_number=None, scale_type="PRM1Z8"):
        """
        Initializes the connection. If no serial number is provided, 
        it auto-connects to the first available Thorlabs device.
        """
        if serial_number is None:
            devices = Thorlabs.list_kinesis_devices()
            if not devices:
                raise ConnectionError("No Thorlabs devices found plugged into the PC.")
            self.serial_number = devices[0][0]
        else:
            self.serial_number = serial_number

        print(f"[Waveplate] Connecting to motor SN: {self.serial_number}...")
        
        # Connect to the motor using the appropriate step-to-degree scale
        self.motor = Thorlabs.KinesisMotor(self.serial_number, scale=scale_type)
        self.is_homed = False

    def home(self, wait=True):
        """Forces the rotation mount to find its physical zero point."""
        print("[Waveplate] Homing... Please wait.")
        self.motor.home()
        if wait:
            self.motor.wait_move()
        self.is_homed = True
        print("[Waveplate] Homing complete.")

    def move_to_degree(self, angle, wait=True):
        """Rotates the waveplate to an absolute angle in degrees."""
        if not self.is_homed:
            print("[Waveplate] Warning: Moving before homing can cause inaccurate angles!")
            
        print(f"[Waveplate] Rotating to {angle}°...")
        self.motor.move_to(angle)
        
        if wait:
            self.motor.wait_move()
            print(f"[Waveplate] Arrived at {self.get_current_angle():.2f}°")

    def get_current_angle(self):
        """Returns the current angle of the waveplate."""
        return self.motor.get_position()

    def close(self):
        """Safely closes the USB connection."""
        if self.motor:
            self.motor.close()
            print("[Waveplate] Connection safely closed.")

    # --- Context Manager Support (Allows using 'with' statements) ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()