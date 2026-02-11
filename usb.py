import pyvisa
import ast

rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")  # your USB address

# Load the TSP file
with open("measure_10s.tsp", "r") as f:
    tsp_code = f.read()

keithley.write(tsp_code)  # send script to instrument

# Call the function and fetch measurements
data_str = keithley.query("print(measure_10s())")

# Convert Lua-like table to Python list
data_str = data_str.replace("nil", "None")
measurements = ast.literal_eval(data_str)

# Print measurements
print("Time (s) | SMUA (A) | SMUB (A)")
for t, i_a, i_b in measurements:
    print(f"{t:.2f} | {i_a:.6e} | {i_b:.6e}")
