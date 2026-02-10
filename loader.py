import pyvisa
import time
import numpy as np
import csv

# --- CONFIG ---
TSP_FILENAME = "pulse_logic.tsp"
DATA_FILE = "final_result.csv"

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 30000 # Long timeout for the test
keithley.read_termination = '\n'

try:
    # 1. READ THE TSP FILE FROM DISK
    with open(TSP_FILENAME, 'r') as f:
        tsp_code = f.read()

    # 2. UPLOAD TO KEITHLEY
    # We wrap it in 'loadscript' so the instrument names it "MyScript"
    print("Uploading script...")
    keithley.write("abort; *cls")
    keithley.write("loadscript MyScript")
    keithley.write(tsp_code)
    keithley.write("endscript")
    keithley.write("MyScript.save()") # Make it survive a reboot (optional)

    # 3. RUN THE FUNCTION
    # Now we just call the function we defined in the file
    print("Running Pulse Sequence...")
    # Arguments: Drain=1V, High=1V, Low=-1V, Width=1s, Cycles=3
    keithley.write("RunPulseSequence(1.0, 1.0, -1.0, 1.0, 3)")
    
    # 4. GET DATA
    # Wait for completion (Total time = 3 cycles * 2 steps * 1s = 6s)
    time.sleep(6.5) 
    
    raw_id = keithley.read()
    raw_ig = keithley.read()
    
    print("Data received. Saving...")
    # (Save logic same as before...)
    
except Exception as e:
    print(f"Error: {e}")
    # Print instrument error if any
    try: print(keithley.query("print(errorqueue.next())"))
    except: pass
finally:
    keithley.close()