import pyvisa
import time

# Connect to the instrument
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")  # your USB address

# Reset channels
keithley.write("smua.reset()")
keithley.write("smub.reset()")

# Configure SMUA
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smua.source.levelv = 1")       # 1 V
keithley.write("smua.source.output = smua.OUTPUT_ON")

# Configure SMUB
keithley.write("smub.source.func = smub.OUTPUT_DCVOLTS")
keithley.write("smub.source.levelv = 1")       # 1 V
keithley.write("smub.source.output = smub.OUTPUT_ON")

# Prepare to store measurements
measurements = []  # list of tuples: (time, i_a, i_b)
duration = 10      # seconds
interval = 0.5     # seconds between measurements

start_time = time.time()
while time.time() - start_time < duration:
    current_time = time.time() - start_time
    i_a = float(keithley.query("print(smua.measure.i())"))
    i_b = float(keithley.query("print(smub.measure.i())"))
    measurements.append((current_time, i_a, i_b))
    print(f"{current_time:.2f} s - SMUA: {i_a:.6e} A, SMUB: {i_b:.6e} A")
    time.sleep(interval)

# Turn off outputs
keithley.write("smua.source.output = smua.OUTPUT_OFF")
keithley.write("smub.source.output = smub.OUTPUT_OFF")

# Optional: print all measurements
print("\nAll measurements collected:")
for t, a, b in measurements:
    print(f"{t:.2f} s - SMUA: {a:.6e} A, SMUB: {b:.6e} A")
