import pyvisa
import time
import csv
import os

# --- CONFIGURATION ---
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" # UPDATE THIS
FILENAME = "shared_data.csv"
DRAIN_V = 1.0       
GATE_HIGH = 1.0     
GATE_LOW = -1.0     
POINTS_PER_PHASE = 30  
CYCLES = 5             

# --- CONNECT ---
try:
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
except:
    print("Connection Failed. Check USB ID.")
    exit()

print("--- INITIALIZING ---")

# ==========================================
# THE NUCLEAR CLEANING BLOCK
# ==========================================
try:
    # 1. Hardware Clear (The "Kick")
    # Tries to send a low-level USB clear signal
    try: keithley.clear()
    except: pass
    
    # 2. Force Abort & Reset (Ignore Errors Here!)
    # We expect these might fail if the instrument is stuck.
    # We just want to force it into a known state.
    try: keithley.write("abort")
    except: pass
    
    try: keithley.write("*rst") 
    except: pass
    
    # 3. Clear the "Syntax Error" from memory
    # *cls deletes the Error -285 you are seeing
    keithley.write("*cls")
    time.sleep(0.5)
    
    # 4. Drain the Error Queue
    # We keep reading errors until the instrument says "0, No Error"
    # This ensures the red "ERR" light goes off.
    while True:
        try:
            err_count = int(float(keithley.query("print(errorqueue.count)")))
            if err_count == 0:
                break
            # Throw away the error message
            keithley.query("print(errorqueue.next())")
        except:
            break

    print("Instrument Clean. Starting Test...")

except Exception as e:
    print(f"Warning during init: {e}")
    # Continue anyway, usually it's fine.

# ==========================================
# THE REAL TEST
# ==========================================

# Prepare File
if os.path.exists(FILENAME):
    try: os.remove(FILENAME)
    except: pass

with open(FILENAME, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])

try:
    start_time = time.time()

    # 1. SETUP (Fast Mode)
    # Now that the instrument is clean, these commands will work perfectly.
    keithley.write(f"smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv={DRAIN_V}")
    keithley.write("smua.source.limiti=0.1; smua.measure.rangei=0.1")
    keithley.write("smua.measure.nplc=0.01; smua.measure.autorangei=0")
    keithley.write("smua.source.output=1")
    
    keithley.write(f"smub.source.func=smua.OUTPUT_DCVOLTS; smub.source.levelv={GATE_LOW}")
    keithley.write("smub.source.limiti=0.1; smub.measure.rangei=0.1")
    keithley.write("smub.measure.nplc=0.01; smub.measure.autorangei=0")
    keithley.write("smub.source.output=1")

    # 2. MAIN LOOP
    for i in range(CYCLES):
        print(f"Cycle {i+1}/{CYCLES}...", end="", flush=True)

        # --- HIGH PHASE ---
        keithley.write(f"smub.source.levelv = {GATE_HIGH}")
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
                f.flush() # Update for plotter

        # --- LOW PHASE ---
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
    print("Finished.")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except: pass