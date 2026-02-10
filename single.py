import pyvisa
import time
import csv
import numpy as np
import os

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0     
GATE_VOLTAGE  = 1.0     
PULSE_WIDTH   = 1.0       
FILENAME      = "single_shot.csv"

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 
keithley.read_termination = '\n'

print(f"--- STARTING SINGLE PULSE TEST ---")

try:
    # 1. RESET & CONFIGURE
    keithley.write("abort; *cls; reset()")
    keithley.write("format.data = format.ASCII")
    keithley.write("display.screen = display.SMUA_SMUB")
    
    # Configure SMU A (Drain)
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write("smua.measure.nplc = 0.01") # Fast
    keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON")

    # Configure SMU B (Gate)
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smub.source.output = smua.OUTPUT_ON")
    keithley.write("smub.measure.nplc = 0.01") # Fast
    keithley.write("smub.measure.autorangei = smua.AUTORANGE_ON")

    # 2. DEFINE THE PULSE (Raw Lua Block)
    # This runs immediately when sent. No functions, no complexity.
    lua_code = f"""
    -- Setup Buffers
    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()
    smua.nvbuffer1.appendmode = 1
    smub.nvbuffer1.appendmode = 1
    
    -- Set Voltage
    smub.source.levelv = {GATE_VOLTAGE}
    
    -- Measure Loop ( Precise Hardware Timing )
    timer.reset()
    start_t = timer.measure.t()
    while (timer.measure.t() - start_t) < {PULSE_WIDTH} do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
    end
    
    -- Return Data
    printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)
    printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)
    """

    print("Sending Pulse Command...")
    keithley.write(lua_code)
    
    # 3. WAIT & READ
    # Critical: Wait for the pulse to actually finish before asking for data
    time.sleep(PULSE_WIDTH + 0.5)
    
    raw_id = keithley.read()
    raw_ig = keithley.read()
    
    # 4. PROCESS DATA
    data_id = np.fromstring(raw_id, sep=',')
    data_ig = np.fromstring(raw_ig, sep=',')
    num_pts = len(data_id)
    
    # Create Time Axis
    times = np.linspace(0, PULSE_WIDTH, num_pts)
    
    print(f"Success! Captured {num_pts} points in {PULSE_WIDTH} seconds.")
    print(f"Sample Rate: {num_pts/PULSE_WIDTH:.0f} points/sec")

    # 5. SAVE
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        for i in range(num_pts):
            writer.writerow([times[i], GATE_VOLTAGE, data_id[i], data_ig[i]])
            
    print(f"Data saved to {FILENAME}")

finally:
    # 6. CLEANUP
    print("Turning OFF.")
    keithley.write("smua.source.output = 0; smub.source.output = 0")
    keithley.close()