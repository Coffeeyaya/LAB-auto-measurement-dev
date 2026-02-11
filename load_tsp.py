import pyvisa
rm = pyvisa.ResourceManager()

RESOURCE = "GPIB0::26::INSTR"
inst = rm.open_resource(RESOURCE)

inst.write_termination = '\n'
inst.read_termination = '\n'

# Delete old script if exists
inst.write("script.delete('gate_sweep')")

# Upload new script line by line
with open("gate_sweep.tsp", "r") as f:
    for line in f:
        if line.strip():  # skip empty lines
            inst.write(line.rstrip())

print("Upload complete.")

# Run the sweep
inst.write("run()")  # call the global function

# Read all output lines from print()
while True:
    try:
        line = inst.read()
        print("Measured current:", line)
    except pyvisa.errors.VisaIOError:
        break
