import pyvisa
import time

# Use the exact port we just verified
AOTF_RESOURCE_ID = 'ASRL3::INSTR' 

rm = pyvisa.ResourceManager()

try:
    print(f"Connecting to AOTF on {AOTF_RESOURCE_ID}...")
    aotf = rm.open_resource(AOTF_RESOURCE_ID)
    
    # Standard serial communication settings
    aotf.timeout = 2000
    aotf.write_termination = '\n'
    aotf.read_termination = '\n'
    print("Connection open.")

    # 1. Enable daughter card for direct command control
    # CAUTION: Ensure pins 33-40 on the MDR connector are not floating!
    aotf.write("DAU EN")
    print("Direct control enabled. GUI settings are now ignored.")

    # 2. Set Channel 0 to 90 MHz
    # Command format: DDS F-p0 [channel] [frequency_in_MHz]
    channel = 0
    freq_mhz = 90.0
    aotf.write(f"DDS F-p0 {channel} {freq_mhz}")
    print(f"Channel {channel} frequency set to {freq_mhz} MHz.")

    # Let it run for 3 seconds so you can verify the output
    print("Holding for 3 seconds...")
    time.sleep(3)

    # 3. Disable direct control and return to default state
    aotf.write("DAU DIS")
    print("Direct control disabled. Control returned to GUI.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Always close the port
    if 'aotf' in locals():
        aotf.close()
        print("Connection safely closed.")