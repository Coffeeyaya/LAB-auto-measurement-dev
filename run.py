import pyvisa

rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")

with open("pulse_measure.tsp", "r") as f:
    tsp_code = f.read()

k.write(tsp_code)
k.write("loadscript pulse_measure")
k.write("endscript")

k.close()
