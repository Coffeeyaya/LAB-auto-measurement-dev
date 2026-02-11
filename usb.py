import pyvisa

rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")

# TSP script: measure SMUA and SMUB current for 10 s with 0.1 s interval
tsp_script = """
smua.reset()
smub.reset()

smua.source.func = smua.OUTPUT_DCVOLTS
smua.source.levelv = 1
smua.source.output = smua.OUTPUT_ON

smub.source.func = smub.OUTPUT_DCVOLTS
smub.source.levelv = 1
smub.source.output = smub.OUTPUT_ON

local measurements = {}
local dt = 0.1       -- 0.1 s interval
local t_end = 10     -- total measurement time
local t = 0

while t < t_end do
    local i_a = smua.measure.i()
    local i_b = smub.measure.i()
    table.insert(measurements, {t, i_a, i_b})
    t = t + dt
    wait(dt)
end

smua.source.output = smua.OUTPUT_OFF
smub.source.output = smub.OUTPUT_OFF

return measurements
"""

# Send script to the instrument and execute
keithley.write("tsp.execute = false")        # optional: stop auto-execution
keithley.write(tsp_script)
data = keithley.query("return measurements")

# Print measurements
print("Time (s) | SMUA (A) | SMUB (A)")
for t, i_a, i_b in data:
    print(f"{t:.2f} | {i_a:.6e} | {i_b:.6e}")
