import pyvisa

rm = pyvisa.ResourceManager()
inst = rm.open_resource("TCPIP0::192.168.1.100::inst0::INSTR")

inst.timeout = 10000
inst.write_termination = '\n'
inst.read_termination = '\n'

print(inst.query("print(localnode.model)"))
inst.write("script.delete('get_sweep')")
inst.write("reset()")
with open("get_sweep.tsp", "r") as f:
    tsp_code = f.read()

inst.write(tsp_code)
print(inst.query("print(script.catalog())"))
inst.write("get_sweep.run()")
data = []

while True:
    try:
        line = inst.read()
        data.append(float(line))
        print("Measured I:", line)
    except:
        break
inst.write("smua.source.output = smua.OUTPUT_OFF")
