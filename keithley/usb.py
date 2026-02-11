import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
# PASTE YOUR USB ID HERE:
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

FILENAME = "usb_fast_data.csv"
DRAIN_V = 1.0       
GATE_HIGH = 1.0     
GATE_LOW = -1.0     

# We will capture exactly 50 points (guaranteed data)
POINTS_TO_CAPTURE = 50 

# --- CONNECT ---
rm = pyvisa.ResourceManager()
try:
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
    print(f"Connected: {keithley.query('*idn?').strip()}")
except:
    print("Connection Failed. Check USB ID.")
    exit()

print("--- STARTING FAST PULSE ---")

try:
    # 1. CLEAN START (Ignore 'Aborted' errors)
    keithley.write("abort")
    keithley.write("*rst")
    keithley.write("*cls") # Clear Status Register
    keithley.write("errorqueue.clear()")
    time.sleep(1.0)

    # 2. SETUP FOR SPEED (Crucial Step!)
    # We turn OFF Auto-Range and set a fixed 100mA limit. 
    # This makes reading 10x faster.
    setup_cmds = [
        "format.data = format.ASCII",
        
        # Drain Setup
        "smua.source.func = smua.OUTPUT_DCVOLTS",
        f"smua.source.levelv = {DRAIN_V}",
        "smua.source.limiti = 0.1",       # 100mA Compliance
        "smua.measure.rangei = 0.1",      # FIXED Range (100mA)
        "smua.measure.nplc = 0.01",       # Fastest Integration
        "smua.measure.autorangei = 0",    # OFF (Critical)
        "smua.source.output = 1",

        # Gate Setup
        "smub.source.func = smua.OUTPUT_DCVOLTS",
        f"smub.source.levelv = {GATE_LOW}",
        "smub.source.limiti = 0.1",       # 100mA Compliance
        "smub.measure.rangei = 0.1",      # FIXED Range (100mA)
        "smub.measure.nplc = 0.01",       # Fastest Integration
        "smub.measure.autorangei = 0",    # OFF (Critical)
        "smub.source.output = 1"
    ]
    
    for cmd in setup_cmds:
        keithley.write(cmd)

    # 3. RUN THE PULSE (Count-Based Loop)
    print(f"Pulsing to {GATE_HIGH}V...")
    
    data_log = []
    start_time = time.time()
    
    # Trigger Pulse
    keithley.write(f"smub.source.levelv = {GATE_HIGH}")
    
    # Capture exactly 'POINTS_TO_CAPTURE' points
    for i in range(POINTS_TO_CAPTURE):
        try:
            # Request Data
            keithley.write("print(smua.measure.i(), smub.measure.i())")
            
            # Read Data
            response = keithley.read()
            
            # Parse
            clean = response.replace('\t', ',')
            parts = clean.split(',')
            
            if len(parts) >= 2:
                t_now = time.time() - start_time
                i_drain = float(parts[0])
                i_gate = float(parts[1])
                data_log.append([t_now, i_drain, i_gate])
            
        except Exception as e:
            # Ignore timeouts, just try next point
            pass

    # End Pulse
    keithley.write(f"smub.source.levelv = {GATE_LOW}")
    print("Pulse Finished.")

    # 4. SAVE
    print(f"Captured {len(data_log)} points.")
    if len(data_log) > 0:
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "I_Drain", "I_Gate"])
            writer.writerows(data_log)
        print(f"SUCCESS! Saved to {FILENAME}")
    else:
        print("FAILURE: 0 points captured.")

except Exception as e:
    print(f"Error: {e}")
    try: print(f"Inst Error: {keithley.query('print(errorqueue.next())')}")
    except: pass

finally:
    print("Closing...")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except: pass