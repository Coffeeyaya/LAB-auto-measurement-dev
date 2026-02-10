import pyvisa
import time

# Connect to the instrument
rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")  # adjust to your address
k.write_termination = "\n"
k.read_termination = "\n"

# Step 1: Hard reset the TSP engine
k.write("abort")    # stop any running commands or scripts
time.sleep(0.2)     # short delay to ensure abort completes

k.write("reset()")  # reset the SMU and TSP engine
time.sleep(5)       # wait ~5 seconds for the instrument to fully reset

# Optional: check basic functionality
print(k.query("print(1+1)"))  # should return 2

# Close connection if done
k.close()
