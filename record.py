import pyvisa

rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.write_termination = "\n"

# 1. Delete existing script (critical)
k.write("script.delete('pulse_measure')")

# 2. Start script definition
k.write("loadscript pulse_measure")

# 3. Script body (NO indentation issues)
k.write("function run_pulse(vds, vgh, vgl, dt, pulse_width, cycles)")
k.write("abort")
k.write("errorqueue.clear()")

k.write("smua.reset()")
k.write("smub.reset()")

k.write("smua.source.func = smua.OUTPUT_DCVOLTS")
k.write("smub.source.func = smub.OUTPUT_DCVOLTS")

k.write("smua.source.limiti = 0.01")
k.write("smub.source.limiti = 0.001")

k.write("smua.measure.nplc = 0.01")
k.write("smub.measure.nplc = 0.01")

k.write("smua.source.levelv = vds")
k.write("smua.source.output = smua.OUTPUT_ON")
k.write("smub.source.output = smub.OUTPUT_ON")

k.write("smua.nvbuffer1.clear()")
k.write("smub.nvbuffer1.clear()")

k.write("smua.nvbuffer1.timestamps = 1")
k.write("smub.nvbuffer1.timestamps = 1")

k.write("npts = math.floor(pulse_width / dt)")

k.write("for c = 1, cycles do")

k.write("smub.source.levelv = vgh")
k.write("for i = 1, npts do")
k.write("smua.measure.i(smua.nvbuffer1)")
k.write("smub.measure.i(smub.nvbuffer1)")
k.write("delay(dt)")
k.write("end")

k.write("smub.source.levelv = vgl")
k.write("for i = 1, npts do")
k.write("smua.measure.i(smua.nvbuffer1)")
k.write("smub.measure.i(smub.nvbuffer1)")
k.write("delay(dt)")
k.write("end")

k.write("end")

k.write("smua.source.levelv = 0")
k.write("smub.source.levelv = 0")
k.write("end")

# 4. End script definition
k.write("endscript")

k.close()
