import pyvisa
import time
import csv
import numpy as np

# --- CONFIG ---
TSP_FILENAME = "pulse.tsp"
FILENAME = "pulse_measurements.csv"
DRAIN_V = 1.0
GATE_V = 1.0
PULSE_WIDTH = 1.0

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 25000 
keithley.write_termination = '\n'
keithley.read_termination = '\n'

print(f"--- ROBUST PULSE TEST ---")

try:
    # 1. RESET INSTRUMENT
    # We start fresh every time to avoid "memory" errors
    keithley.write("abort")
    keithley.write("*rst") 
    keithley.write("errorqueue.clear()")
    time.sleep(0.5)

    # 2. DEFINE THE FUNCTION (The "Slow Load" Method)
    # We read the file and send it line-by-line to define 'RunPulse' globally.
    # We do NOT use 'loadscript' here, just direct definition.
    print(f"Loading {TSP_FILENAME}...")
    with open(TSP_FILENAME, 'r') as f:
        lines = f.readlines()

    for line in lines:
        cleaned = line.strip()
        # Skip empty lines and comments
        if cleaned and not cleaned.startswith("--"):
            keithley.write(cleaned)
            time.sleep(0.02) # Fast but safe delay

    # Check if the function loaded okay
    err_count = int(float(keithley.query("print(errorqueue.count)")))
    if err_count > 0:
        raise Exception(f"Syntax Error in TSP file: {keithley.query('print(errorqueue.next())')}")

    # 3. RUN THE PULSE
    print(f"Executing RunPulse({DRAIN_V}, {GATE_V}, {PULSE_WIDTH})...")
    keithley.write(f"RunPulse({DRAIN_V}, {GATE_V}, {PULSE_WIDTH})")

    # 4. WAIT FOR COMPLETION
    # Pulse Width + 1.0s safety buffer
    time.sleep(PULSE_WIDTH + 1.0)

    # 5. RETRIEVE DATA
    # First, read the point count (the script prints this at the end)
    try:
        response = keithley.read()
        num_points = int(float(response))
        print(f"Captured {num_points} points.")
    except Exception as e:
        # If read fails, ask the error queue why
        err = keithley.query("print(errorqueue.next())")
        raise Exception(f"Failed to get point count. Instrument says: {err}")

    if num_points == 0:
        print("Warning: 0 points captured.")
    else:
        # Download Buffers
        print("Downloading Drain Current...")
        keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
        raw_id = keithley.read()
        
        print("Downloading Gate Current...")
        keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
        raw_ig = keithley.read()
        
        # 6. SAVE
        data_id = np.fromstring(raw_id, sep=',')
        data_ig = np.fromstring(raw_ig, sep=',')
        times = np.linspace(0, PULSE_WIDTH, num_points)
        
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
            for t, i_d, i_g in zip(times, data_id, data_ig):
                writer.writerow([t, GATE_V, i_d, i_g])
                
        print(f"Success! Data saved to {FILENAME}")

except Exception as e:
    print(f"\n[ERROR] {e}")

finally:
    # Safety Shutdown
    keithley.write("smua.source.output = 0")
    keithley.write("smub.source.output = 0")
    keithley.close()