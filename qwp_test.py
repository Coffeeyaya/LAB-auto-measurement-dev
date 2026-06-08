from pylablib.devices import Thorlabs
import time

def spin_360():
    # 1. Connect (Auto-finds the first device)
    devices = Thorlabs.list_kinesis_devices()
    if not devices:
        print("❌ No Thorlabs devices found.")
        return
        
    serial_number = devices[0][0]
    print(f"🔌 Connecting to SN: {serial_number}")
    
    # Notice we REMOVED the scale="PRM1Z8" parameter here!
    # We are operating purely in raw hardware steps now.
    motor = Thorlabs.KinesisMotor(serial_number)

    try:
        # 2. Homing
        print("🏠 Homing... (Look at the stage, it should be moving slowly)")
        motor.home()
        motor.wait_move()
        print("✅ Homing complete. At 0 degrees.")

        # 3. The Math for 360 Degrees
        # The PRM1Z8 requires 1919.641 steps to move exactly 1 degree
        steps_per_degree = 1919.641
        target_degrees = 360.0
        
        target_steps = int(target_degrees * steps_per_degree)
        
        print(f"🔄 Commanding a {target_degrees}° rotation ({target_steps} raw steps)...")
        
        # 4. Move
        motor.move_to(target_steps)
        motor.wait_move() # Wait until it finishes spinning
        
        print("🎯 Rotation complete!")

    except Exception as e:
        print(f"⚠️ Error: {e}")
        
    finally:
        motor.close()
        print("🔒 Connection closed.")

if __name__ == "__main__":
    spin_360()