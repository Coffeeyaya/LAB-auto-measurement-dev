import pyvisa
import time
import csv
import os

# --- CONFIGURATION ---
FILENAME = "live_measurements.csv"
DRAIN_VOLTAGE = 1.0     
GATE_HIGH = 1.0         
GATE_LOW = -1.0         
PULSE_WIDTH = 1.0       
TOTAL_CYCLES = 5        

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR') 

# Stability Settings
keithley.timeout = 10000 
keithley.read_termination = '\n'
keithley.write_termination = '\n'

print("--- STARTING DUAL-DISPLAY RECORDER ---")

try:
    # 1. INITIALIZATION
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    
    # --- COMMAND 1: Set Display to Dual Mode (Split Screen) ---
    # SMUA_SMUB means: Top half = SMU A, Bottom half = SMU B
    keithley.write("display.screen = display.SMUA_SMUB") 
    
    # --- COMMAND 2: Enable Auto-Range (Measurement) ---
    # This allows the instrument to switch ranges automatically (e.g., mA -> uA -> nA)
    # consistent with the signal level.
    keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON")
    keithley.write("smub.measure.autorangei = smua.AUTORANGE_ON")
    
    # (Optional) Enable Source Auto-Range if you want the source to adapt too
    keithley.write("smua.source.autorangev = smua.AUTORANGE_ON")
    keithley.write("smub.source.autorangev = smua.AUTORANGE_ON")

    # Standard Setup
    keithley.write("format.data = format.ASCII")
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smub.source.output = smua.OUTPUT_ON")
    keithley.write(f"smub.source.levelv = {GATE_HIGH}")

    # 2. RECORDING LOOP
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        
        start_exp = time.time()
        
        for cycle in range(TOTAL_CYCLES):
            for v_gate in [GATE_HIGH, GATE_LOW]:
                
                # Switch Voltage
                keithley.write(f"smub.source.levelv = {v_gate}")
                step_start = time.time()
                print(f"Cycle {cycle+1}: Gate {v_gate}V")
                
                # Loop for precise duration
                while (time.time() - step_start) < PULSE_WIDTH:
                    try:
                        # Query Data
                        raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                        vals = raw.strip().split()
                        
                        t_now = time.time() - start_exp
                        
                        # Save
                        writer.writerow([t_now, v_gate, vals[0], vals[1]])
                        f.flush() 
                        
                    except ValueError:
                        pass
                        
finally:
    print("Finished. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()