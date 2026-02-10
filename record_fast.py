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

# 1. Connection Speed Settings
keithley.timeout = 10000 
keithley.read_termination = '\n'
keithley.write_termination = '\n'

print("--- STARTING HIGH-SPEED RECORDER ---")

try:
    # 2. SPEED OPTIMIZATION (The "Turbo" Button)
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    
    # Set NPLC to 0.01 (Fastest measurement)
    # Default is 1.0. This makes it 100x faster.
    keithley.write("smua.measure.nplc = 0.01")
    keithley.write("smub.measure.nplc = 0.01")
    
    # Turn off Auto-Zero (Doubles speed)
    keithley.write("smua.measure.autozero = smua.AUTOZERO_OFF")
    keithley.write("smub.measure.autozero = smua.AUTOZERO_OFF")
    
    # Turn off Auto-Range (Prevents delays from range switching)
    # We lock it to the 2V range (assuming your signals are < 2V)
    keithley.write("smua.source.rangev = 2")
    keithley.write("smua.measure.rangei = 1e-3") # Set this to expected current range!
    keithley.write("smub.source.rangev = 2")
    
    # Turn off Display (Saves CPU time on instrument)
    keithley.write("display.screen = display.OFF")

    # Standard Setup
    keithley.write("format.data = format.ASCII")
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smub.source.output = smua.OUTPUT_ON")
    keithley.write(f"smub.source.levelv = {GATE_HIGH}")

    # 3. RECORDING LOOP
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
                
                # Fast Loop
                while (time.time() - step_start) < PULSE_WIDTH:
                    try:
                        # Query Data
                        raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                        vals = raw.strip().split()
                        
                        t_now = time.time() - start_exp
                        
                        # Save
                        writer.writerow([t_now, v_gate, vals[0], vals[1]])
                        
                        # OPTIMIZED FLUSH: Only flush, don't force disk sync
                        # This is much faster than os.fsync()
                        f.flush() 
                        
                    except ValueError:
                        pass
                        
finally:
    print("Finished. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.write("display.screen = display.ON") # Turn screen back on!
    keithley.close()