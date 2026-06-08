from pylablib.devices import Thorlabs
import time

def test_waveplate_motor():
    # 1. SCAN FOR DEVICES
    # This will print out a list of all Thorlabs serial numbers plugged into USB
    connected_devices = Thorlabs.list_kinesis_devices()
    print(f"🔍 Found Thorlabs devices: {connected_devices}")
    
    if not connected_devices:
        print("❌ No devices found. Check your USB cable and power supply!")
        return

    # Grab the first device in the list (Usually starts with '27' for K-Cubes)
    # If you have multiple devices, you will hardcode your serial number here instead
    serial_number = connected_devices[0][0] 
    print(f"🔌 Connecting to K-Cube (SN: {serial_number})...")

    # 2. CONNECT TO THE MOTOR
    # Note: Kinesis motors use internal 'device units' (raw encoder steps). 
    # To use degrees, you pass a scaling factor. For PRM1Z8, the scale is usually 1919.64 steps/degree.
    # If it acts weird, simply remove the `scale` argument and use raw steps.
    waveplate = Thorlabs.KinesisMotor(serial_number, scale="PRM1Z8")

    try:
        # 3. HOMING (Crucial!)
        # The motor must find its physical zero point before it knows where 45 degrees is.
        print("🏠 Homing the rotation mount (this may take 10-20 seconds)...")
        waveplate.home()
        waveplate.wait_move() # Pauses Python until the motor stops moving
        print("✅ Homing complete.")

        # 4. ROTATE THE WAVEPLATE
        target_angle = 45.0
        print(f"🔄 Rotating to {target_angle} degrees...")
        waveplate.move_to(target_angle)
        waveplate.wait_move()
        
        current_pos = waveplate.get_position()
        print(f"🎯 Arrived at: {current_pos:.2f} degrees")
        
        # Hold there for a moment
        time.sleep(2)

        # Move back to 0
        print("⏪ Returning to 0 degrees...")
        waveplate.move_to(0)
        waveplate.wait_move()

    except Exception as e:
        print(f"⚠️ An error occurred: {e}")
        
    finally:
        # 5. SAFELY DISCONNECT
        # If you don't close the connection, Python holds the USB port hostage!
        waveplate.close()
        print("🔒 Connection closed.")

if __name__ == "__main__":
    test_waveplate_motor()