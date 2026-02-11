import pyvisa

rm = pyvisa.ResourceManager()
RESOURCE = "GPIB0::26::INSTR"
inst = rm.open_resource(RESOURCE)

inst.write("script.delete('get_sweep')")

with open("get_sweep.tsp", "r") as f:
    for line in f:
        inst.write(line.rstrip())

print("Upload complete.")
inst.write("get_sweep.run()")
inst.write("smua.source.output = suma.OUTPUT_OFF")
