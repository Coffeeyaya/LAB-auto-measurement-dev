import pyvisa
import time
import ast  # to parse returned data

rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")

# Define a TSP function to run on the instrument
tsp_script = """
function measure_fast()
    local meas = {}        -- local table to store measurements
    smua.reset()
    smub.reset()
    
    smua.source.func = smua.OUTPUT_DCVOLTS
    smua.source.levelv = 1
    smua.source.output = smua.OUTPUT_ON
    
    smub.source.func = smub.OUTPUT_DCVOLTS
    smub.source.levelv = 1
    smub.source.output = smub.OUTPUT_ON
    
    local dt = 0.1
    local t_end = 10
    local t = 0
    while t < t_end do
        local i_a = smua.measure.i()
        local i_b = smub.measure.i()
        table.insert(meas, {t, i_a, i_b})
        t = t + dt
        wait(dt)
    end
    
    smua.source.output = smua.OUTPUT_OFF
    smub.source.output = smub.OUTPUT_OFF
    
    return meas
end
"""

# Send the function to the instrument
keithley.write(tsp_script)

# Call the function and fetch measurements
data_str = keithley.query("print(measure_fast())")

# Convert string to Python list (TSP returns Lua-like table)
# Replace 'nil' with 'None' just in case
data_str = data_str.replace("nil", "None")
measurements = ast.literal_eval(data_str)

# Print results
print("Time (s) | SMUA (A) | SMUB (A)")
for t, i_a, i_b in measurements:
    print(f"{t:.2f} | {i_a:.6e} | {i_b:.6e}")
