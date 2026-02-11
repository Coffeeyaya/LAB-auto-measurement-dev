import pyvisa
import time
import csv
import os

# --- CONFIGURATION ---
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" # Update this!
FILENAME = "shared_data.csv"
DRAIN_V = 1.0       
GATE_HIGH = 1.0     
GATE_LOW = -1.0     
POINTS_PER_PHASE = 50 
CYCLES = 5             

# Delete old file so the plotter knows we started fresh
if os.path.exists(FILENAME):
    os.remove(FILENAME)

# Create file with Header
with open(FILENAME, 'w', newline='', buffering=1) as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])

print("--- STARTING MEASUREMENT ---")

# --- CONNECT ---
try:
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
except:
    print("Connection Failed.")
    exit()

try:
    # --- 1. THE CLEANING BLOCK (Fixes Error -285) ---
    print("Cleaning buffer...")
    try:
        keithley.clear() # Sends a low-level USB "Device Clear" signal
    except:
        pass
        
    # Read any junk left in the output buffer
    try:
        keithley.read() 
    except:
        pass # It's okay if there is nothing to read
        
    # NOW start your real setup
    keithley.write("abort; *cls") # *cls deletes the old -285 error from memory
    keithley.write("*rst")
    
    # Drain Setup
    keithley.write(f"smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv={DRAIN_V}")
    keithley.write("smua.source.limiti=0.1; smua.measure.rangei=0.1")
    keithley.write("smua.measure.nplc=0.01; smua.measure.autorangei=0")
    keithley.write("smua.source.output=1")
    
    # Gate Setup
    keithley.write(f"smub.source.func=smua.OUTPUT_DCVOLTS; smub.source.levelv={GATE_LOW}")
    keithley.write("smub.source.limiti=0.1; smub.measure.rangei=0.1")
    keithley.write("smub.measure.nplc=0.01; smub.measure.autorangei=0")
    keithley.write("smub.source.output=1")

    start_time = time.time()
    
    # 2. MAIN LOOP
    for i in range(CYCLES):
        print(f"Cycle {i+1}/{CYCLES}...", end="", flush=True)

        # --- A. HIGH PHASE ---
        keithley.write(f"smub.source.levelv = {GATE_HIGH}")
        
        # Open file in APPEND mode for this chunk
        with open(FILENAME, 'a', newline='') as f:
            writer = csv.writer(f)
            
            for _ in range(POINTS_PER_PHASE):
                try:
                    keithley.write("print(smua.measure.i(), smub.measure.i())")
                    resp = keithley.read().replace('\t', ',').split(',')
                    if len(resp) >= 2:
                        t = time.time() - start_time
                        writer.writerow([t, GATE_HIGH, float(resp[0]), float(resp[1])])
                except: pass
                
                # CRITICAL: Flush to disk occasionally so Plotter sees it
                # We do it every point here for maximum "real-time" feel, 
                # or every 10 points for speed.
                f.flush() 

        # --- B. LOW PHASE ---
        keithley.write(f"smub.source.levelv = {GATE_LOW}")
        
        with open(FILENAME, 'a', newline='') as f:
            writer = csv.writer(f)
            for _ in range(POINTS_PER_PHASE):
                try:
                    keithley.write("print(smua.measure.i(), smub.measure.i())")
                    resp = keithley.read().replace('\t', ',').split(',')
                    if len(resp) >= 2:
                        t = time.time() - start_time
                        writer.writerow([t, GATE_LOW, float(resp[0]), float(resp[1])])
                except: pass
                f.flush()

        print(" Done.")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Safety Shutdown
    print("Measurement Finished.")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except: pass