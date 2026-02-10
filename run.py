import pyvisa
import time
import csv
import numpy as np

rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.write_termination = '\n'

# CALL THE FUNCTION WE JUST LOADED
# RunPulse(Drain=1V, Gate=1V, Width=1.0s, Points=ignored)
print("Running Pulse...")
keithley.write("RunPulse(1.0, 1.0, 1.0, 0)")

# Wait for pulse to finish (1.0s + buffer)
time.sleep(1.5)

# GET DATA
# The script prints the count at the end, so we read that first
count = int(float(keithley.read()))
print(f"Instrument captured {count} points.")

# Download buffers
print("Downloading buffers...")
keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
raw_id = keithley.read()
keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
raw_ig = keithley.read()

# Save to CSV (Same as before...)
print("Done.")
keithley.close()