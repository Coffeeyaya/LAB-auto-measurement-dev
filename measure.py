import pyvisa
import time
import csv
import numpy as np

# --- CONFIG ---
FILENAME = "pulse_data.csv"
DRAIN_V = 1.0
GATE_V = 1.0     
PULSE_WIDTH = 1.0 

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 
keithley.read_termination = '\n'

print("--- RUNNING MEASUREMENT ---")

try:
    # 1. ACTIVATE SCRIPT (Crucial Step!)
    # This 'unpacks' the function into memory so we can use it
    keithley.write("MyPulseTest()") 
    
    # 2. RUN PULSE
    print(f"Pulsing {GATE_V}V for {PULSE_WIDTH}s...")
    keithley.write(f"RunPulse({DRAIN_V}, {GATE_V}, {PULSE_WIDTH})")
    
    # 3. WAIT
    time.sleep(PULSE_WIDTH + 1.0)
    
    # 4. GET DATA
    # Read the number of points first
    num_points = int(float(keithley.read()))
    print(f"Captured {num_points} points.")

    # Download Buffers
    keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
    raw_id = keithley.read()
    
    keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
    raw_ig = keithley.read()
    
    # 5. SAVE
    data_id = np.fromstring(raw_id, sep=',')
    data_ig = np.fromstring(raw_ig, sep=',')
    times = np.linspace(0, PULSE_WIDTH, num_points)
    
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        for t, i_d, i_g in zip(times, data_id, data_ig):
            writer.writerow([t, GATE_V, i_d, i_g])
            
    print(f"Saved to {FILENAME}")

except Exception as e:
    print(f"Error: {e}")
    try: print(f"Instrument Error: {keithley.query('print(errorqueue.next())')}")
    except: pass

finally:
    keithley.close()