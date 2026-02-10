import pyvisa
import time
import csv
import numpy as np
import os

# --- CONFIGURATION ---
FILENAME = "buffer_data.csv"
DRAIN_VOLTAGE = 1.0     
GATE_HIGH = 1.0         
GATE_LOW = -1.0         
PULSE_WIDTH = 1.0       # Precision Pulse Width (s)
TOTAL_CYCLES = 5        

# --- TSP SCRIPT (Internal Engine) ---
tsp_code = """
function MeasurePulse(gate_volts, duration)
    -- Configure Buffers
    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()
    smua.nvbuffer1.appendmode = 1
    smub.nvbuffer1.appendmode = 1
    
    -- Set Voltage
    smub.source.levelv = gate_volts
    
    -- Measure Loop
    timer.reset()
    start_t = timer.measure.t()
    while (timer.measure.t() - start_t) < duration do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
    end
    
    -- Return Data
    printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)
    printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)
end
"""

# --- SETUP ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 
keithley.read_termination = '\n'

print("--- STARTING BUFFER RECORDER ---")
print(f"Saving to: {FILENAME}")

try:
    # 1. Initialize Instrument
    keithley.write("abort; *cls")
    keithley.write("loadscript BurstMeasure\n" + tsp_code + "\nendscript")
    keithley.write("BurstMeasure.save()")
    
    # Speed & Display Settings
    keithley.write("smua.measure.nplc = 0.01")     
    keithley.write("smub.measure.nplc = 0.01")
    keithley.write("display.screen = display.SMUA_SMUB") 
    keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON") 
    keithley.write("smub.measure.autorangei = smua.AUTORANGE_ON")

    # Turn On
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write("smub.source.output = smua.OUTPUT_ON")

    # 2. Main Loop
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        f.flush()
        
        start_exp = time.time()
        
        for cycle in range(TOTAL_CYCLES):
            for v_gate in [GATE_HIGH, GATE_LOW]:
                print(f"Cycle {cycle+1}: Pulsing {v_gate}V... ", end="", flush=True)
                
                # Trigger the 1.0s Pulse
                keithley.write(f"MeasurePulse({v_gate}, {PULSE_WIDTH})")
                
                try:
                    # Read Buffer
                    raw_id = keithley.read()
                    raw_ig = keithley.read()
                    
                    # Process Data
                    data_id = np.fromstring(raw_id, sep=',')
                    data_ig = np.fromstring(raw_ig, sep=',')
                    num_pts = len(data_id)
                    
                    # Create Timestamps
                    t_end = time.time() - start_exp
                    t_start = t_end - PULSE_WIDTH
                    t_chunk = np.linspace(t_start, t_end, num_pts)
                    
                    print(f"Captured {num_pts} points.")
                    
                    # Save to Disk
                    for i in range(num_pts):
                        writer.writerow([t_chunk[i], v_gate, data_id[i], data_ig[i]])
                    
                    f.flush()
                    os.fsync(f.fileno())
                    
                except Exception as e:
                    print(f"Error reading buffer: {e}")

finally:
    print("\nMeasurement Done.")
    
    # --- SAFETY SHUTDOWN (Updated) ---
    print("Ramping voltages to 0 V...")
    keithley.write("smua.source.levelv = 0")
    keithley.write("smub.source.levelv = 0")
    
    time.sleep(0.5) # Wait briefly to ensure 0V is reached
    
    print("Turning outputs OFF...")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    
    keithley.close()