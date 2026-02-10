import pyvisa
import time

rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.write_termination = "\n"
k.read_termination = "\n"
k.timeout = 10000

# --- Step 1: Reset instrument ---
k.write("abort")
time.sleep(0.2)
k.write("reset()")
time.sleep(3)

# --- Step 2: Load minimal script ---
tsp_lines = [
    "loadscript test_script",
    "function simple_set_voltage(vds)",
    "smua.reset()",
    "smua.source.func = smua.OUTPUT_DCVOLTS",
    "smua.source.levelv = vds",
    "smua.source.output = smua.OUTPUT_ON",
    "end",
    "endscript"
]

# Send line by line with a tiny delay
for line in tsp_lines:
    k.write(line)
    time.sleep(0.05)

time.sleep(1)  # wait for script to register

# --- Step 3: Run the function ---
k.write("test_script.simple_set_voltage(1.0)")

# --- Step 4: Turn off output ---
k.write("smua.source.output = smua.OUTPUT_OFF")

k.close()
print("Minimal test complete.")
