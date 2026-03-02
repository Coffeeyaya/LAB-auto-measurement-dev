import time
import csv
import numpy as np
from keithley import Keithley2636B 

# --- CONFIGURATION ---
USB_ID = "USB0::0x05E6::0x2636::4407529::INSTR"
FILENAME = "idvg_curve.csv"

# Sweep Parameters
V_D = 1.0         # Constant Drain Voltage
GATE_START = -2.0     # Starting Gate Voltage (Usually OFF state)
GATE_STOP = 2.0       # Ending Gate Voltage (Usually ON state)
STEPS = 101            # Number of points (41 points from -2 to +2 = 0.1V steps)
SETTLE_DELAY = 0.1    # Time to wait after changing Vg before measuring (seconds)

# Generate the array of voltage points to step through
vg_points = np.linspace(GATE_START, GATE_STOP, STEPS)

print(f"--- STARTING Id-Vg SWEEP ({STEPS} points) ---")

try:
    
    # 1. INITIALIZE
    k26 = Keithley2636B(USB_ID)
    k26.connect()
    k26.clean_instrument()
    k26.config()
    
    # CRITICAL OVERRIDE FOR SWEEPS: Turn Auto-Range ON
    # We need this because Id changes by orders of magnitude.
    k26.keithley.write("smua.measure.autorangei = 1")
    k26.keithley.write("smub.measure.autorangei = 1")
    
    # Increase NPLC slightly for better accuracy on tiny OFF-currents
    k26.keithley.write("smua.measure.nplc = 1.0") 
    k26.keithley.write("smub.measure.nplc = 1.0")
    
    # 3. PREPARE OUTPUTS
    k26.set_Vd(V_D)
    k26.set_Vg(GATE_START)
    k26.enable_output('a', True)
    k26.enable_output('b', True)
    
    # Wait a bit longer at the very beginning for the first state to stabilize
    time.sleep(0.5) 
    start_time = time.time()
    # 4. RUN THE SWEEP
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time","V_D","V_G","I_D","I_G"])
        
        for i, vg in enumerate(vg_points):
            # A. Step the Gate Voltage
            k26.set_Vg(vg)
            
            # B. Wait for the physics to catch up (capacitance charging)
            time.sleep(SETTLE_DELAY)
            t = time.time() - start_time
            # C. Measure
            ia, ib = k26.measure()
            
            if ia is not None:
                # Print progress to console
                print(f"Point {i+1}/{STEPS} | Vg: {vg:+.2f} V | Id: {ia:.2e} A")
                
                # Save to file
                writer.writerow([t, V_D, vg, ia, ib])
                f.flush() # Ensure it saves immediately

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")

finally:
    # 5. SAFE EXIT
    if 'k26' in locals():
        k26.shutdown()