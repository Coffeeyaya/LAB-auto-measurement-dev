import pyvisa
import time
import csv
import numpy as np

# --- SETTINGS ---
FILENAME = "clean_pulse.csv"
VOLTAGE = 1.0
DURATION = 1.0

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 
keithley.write_termination = '\n' 
keithley.read_termination = '\n'

# 1. PREPARE INSTRUMENT (Send one by one to avoid syntax errors)
print("Configuring instrument...")
keithley.write("abort")
keithley.write("*rst") # Hard Reset
keithley.write("errorqueue.clear()")
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smua.measure.nplc = 0.01") # Fast measurement
keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON")
keithley.write("display.screen = display.SMUA_SMUB")

# 2. DEFINE THE PULSE SCRIPT
# We create a clean list of lines, then join them. 
# This guarantees NO hidden spaces or newlines at the start.
tsp_script = [
    "smua.nvbuffer1.clear()",
    "smua.nvbuffer1.appendmode = 1",
    f"smua.source.levelv = {VOLTAGE}",
    "smua.source.output = smua.OUTPUT_ON",
    
    # The Measurement Loop (Runs inside Keithley)
    "timer.reset()",
    "start_t = timer.measure.t()",
    f"while (timer.measure.t() - start_t) < {DURATION} do",
    "   smua.measure.i(smua.nvbuffer1)",
    "end",
    
    "smua.source.output = smua.OUTPUT_OFF",
    "printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)"
]

# Join into one solid block of code
cmd_string = "\n".join(tsp_script)

try:
    print(f"Sending {DURATION}s pulse...")
    
    # 3. SEND & RUN
    keithley.write(cmd_string)
    
    # 4. WAIT & READ
    # Wait for pulse to finish + 0.5s buffer
    time.sleep(DURATION + 0.5)
    
    # Read the data back
    raw_data = keithley.read()
    
    # 5. PROCESS & SAVE
    data_array = np.fromstring(raw_data, sep=',')
    num_points = len(data_array)
    time_axis = np.linspace(0, DURATION, num_points)
    
    print(f"Captured {num_points} points.")
    
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time_s", "Voltage_V", "Current_A"])
        for t, i in zip(time_axis, data_array):
            writer.writerow([t, VOLTAGE, i])
            
    print(f"Saved to {FILENAME}")

except pyvisa.VisaIOError as e:
    # If error occurs, ask the Keithley WHY.
    print(f"\nCOMMUNICATION ERROR: {e}")
    err = keithley.query("print(errorqueue.next())")
    print(f"Instrument says: {err}")

finally:
    keithley.close()