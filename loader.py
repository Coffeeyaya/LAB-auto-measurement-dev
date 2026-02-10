import pyvisa
import time

# --- CONFIG ---
TSP_FILENAME = "pulse.tsp"
SCRIPT_NAME = "MyPulseTest"  # Name inside the Keithley

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000
keithley.write_termination = '\n'
keithley.read_termination = '\n'

print(f"--- LOADING {TSP_FILENAME} VIA GPIB ---")

try:
    # 1. READ FILE
    with open(TSP_FILENAME, 'r') as f:
        lines = f.readlines()

    # 2. PREPARE INSTRUMENT
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    
    # 3. START LOADING
    # We tell Keithley: "I am about to type a script named 'MyPulseTest'"
    print(f"Creating script '{SCRIPT_NAME}'...")
    keithley.write(f"loadscript {SCRIPT_NAME}")
    
    # 4. SEND LINE BY LINE (The Fix)
    for line in lines:
        stripped = line.strip()
        if stripped: # Skip empty lines
            keithley.write(stripped)
            # CRITICAL: Tiny pause to let Keithley compile the line
            time.sleep(0.05) 
            
    # 5. FINISH LOADING
    keithley.write("endscript")
    keithley.write(f"{SCRIPT_NAME}.save()") # Save to non-volatile memory
    
    # 6. CHECK FOR ERRORS
    err_count = int(float(keithley.query("print(errorqueue.count)")))
    if err_count == 0:
        print("SUCCESS! Script loaded without errors.")
        print("You can now call 'RunPulse(...)' anytime.")
    else:
        print(f"FAILED. Found {err_count} syntax errors:")
        print(keithley.query("print(errorqueue.next())"))

except Exception as e:
    print(f"System Error: {e}")

finally:
    keithley.close()