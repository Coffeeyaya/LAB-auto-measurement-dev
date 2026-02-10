import pyvisa
import time

rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.write_termination = "\n"
k.read_termination = "\n"
k.timeout = 20000  # 20 seconds for potentially long queries

# Ensure TSP engine is ready
k.write("abort")
time.sleep(1)
k.write("language = language.TSP")
time.sleep(5)  # wait for TSP engine to fully initialize

# Query existing scripts
try:
    scripts = k.query("print(script.list())")
    print("Existing scripts:", scripts)
except Exception as e:
    print("Query failed:", e)
