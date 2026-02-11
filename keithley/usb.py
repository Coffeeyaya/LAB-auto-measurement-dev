import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
# PASTE YOUR LONG USB ID HERE:
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

FILENAME = "usb_pulse_data.csv"
DRAIN_V = 1.0       # Volts
GATE_HIGH = 1.0     # Volts
GATE_LOW = -1.0     # Volts
PULSE_WIDTH = 1.0   # Seconds

# --- CONNECT ---
try:
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
    
    # Verify Connection
    idn = keithley.query("*idn?")
    print(f"Connected to: {idn.strip()}")

except Exception as e:
    print(f"CONNECTION ERROR: {e}")
    print("Make sure you pasted the correct USB address from Step 1.")
    exit()

print("--- STARTING USB PULSE TEST ---")

try:
    # 1. SETUP (Standard SCPI commands)
    print("Resetting instrument...")
    keithley.write("abort")
    keithley.write("*rst")
    keithley.write("smua.reset()")
    keithley.write("smub.reset()")
    time.sleep(1.0) # Wait for reset

    # Setup SMU A (Drain)
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smua.source.levelv = {DRAIN_V}")
    keithley.write("smua.measure.autorangei = 1")
    keithley.write("smua.source.output = 1")

    # Setup SMU B (Gate)
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smub.source.levelv = {GATE_LOW}")
    keithley.write("smub.measure.autorangei = 1")
    keithley.write("smub.source.output = 1")
    
    # 2. RUN PULSE (Python Control Loop)
    print(f"Pulsing Gate to {GATE_HIGH}V...")
    
    data_log = []
    start_time = time.time()
    
    # A. Set High
    keithley.write(f"smub.source.levelv = {GATE_HIGH}")
    
    # B. Measure Loop
    pulse_start = time.time()
    while (time.time() - pulse_start) < PULSE_WIDTH:
        # Ask for 4 values: V_a, I_a, V_b, I_b
        # We use 'iv' to get both V and I at the same time
        keithley.write("print(smua.measure.iv(), smub.measure.iv())")
        response = keithley.read()
        
        # Response format: "Va, Ia, Vb, Ib" (tab or comma separated)
        # We replace tabs with commas just in case
        clean_resp = response.replace('\t', ',')
        vals = [float(x) for x in clean_resp.split(',')]
        
        # Save: [Time, Drain_I, Gate_I]
        # vals[0]=Va, vals[1]=Ia, vals[2]=Vb, vals[3]=Ib
        t_now = time.time() - start_time
        data_log.append([t_now, vals[1], vals[3]])
        
        # No sleep needed via USB, it's fast enough!

    # C. Set Low (Recovery)
    print(f"Returning Gate to {GATE_LOW}V...")
    keithley.write(f"smub.source.levelv = {GATE_LOW}")
    
    # 3. SAVE
    print(f"Captured {len(data_log)} points.")
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "I_Drain", "I_Gate"])
        writer.writerows(data_log)
        
    print(f"Saved to {FILENAME}")

except Exception as e:
    print(f"\nERROR: {e}")

finally:
    print("Shutting down.")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except:
        pass