import pyvisa
rm = pyvisa.ResourceManager()

RESOURCE = "GPIB0::26::INSTR"
inst = rm.open_resource(RESOURCE)

inst.write_termination = '\n'
inst.read_termination = '\n'
try:
    inst.write("script.delete('gate_sweep')")
except:
    print('not exists')
    
# Upload as before line-by-line
with open("gate_sweep.tsp") as f:
    for line in f:
        if line.strip():
            inst.write(line.rstrip())

inst.write("run()")  

data = []
while True:
    try:
        line = inst.read()
        data.append(float(line))
    except pyvisa.errors.VisaIOError:
        break

print("Sweep data:", data)
