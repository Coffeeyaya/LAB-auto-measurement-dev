import pyvisa
import time
import csv
import os

# --- CONFIGURATION ---
FILENAME = "live_measurements.csv"
DRAIN_VOLTAGE = 1.0     # Volts
GATE_HIGH = 1.0         # Volts
GATE_LOW = -1.0         # Volts
PULSE_WIDTH = 1.0       # Exact duration (Seconds)
TOTAL_CYCLES = 5        # Number of loops

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR') 

# Stability Settings
keithley.timeout = 10000 
keithley.read_termination = '\n'
keithley.write_termination = '\n'

print(f"--- STARTING RECORDER ---")
print(f"Data file: {FILENAME}")
print("You can now run 'plot.py' in a separate terminal.")

try:
    # 1. Initialize Hardware
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    keithley.write("format.data = format.ASCII")
    keithley.write("smua.reset(); smua.source.output = smua.OUTPUT_ON")
    keithley.write("smub.reset(); smub.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")

    # 2. Open File
    # 'w' mode overwrites the file each time you run the script
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        f.flush() # Ensure header is written physically to disk

        start_exp = time.time()

        for cycle in range(TOTAL_CYCLES):
            for v_gate in [GATE_HIGH, GATE_LOW]:
                
                # --- CRITICAL TIMING SECTION ---
                keithley.write(f"smub.source.levelv = {v_gate}")
                step_start = time.time()
                print(f"Cycle {cycle+1}: Gate -> {v_gate} V")
                
                # Stay in this loop for exactly PULSE_WIDTH seconds
                while (time.time() - step_start) < PULSE_WIDTH:
                    try:
                        # Measure
                        raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                        vals = raw.strip().split()
                        
                        # Timestamp
                        t_now = time.time() - start_exp
                        
                        # Save
                        writer.writerow([t_now, v_gate, vals[0], vals[1]])
                        
                        # CRITICAL: Flush buffer so plot.py can see data immediately
                        f.flush() 
                        os.fsync(f.fileno()) 
                        
                    except ValueError:
                        pass
                        
finally:
    print("Recording finished. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()