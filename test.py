import pyvisa

rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')

# The TSP commands written in Lua
tsp_commands = [
    "smua.reset()",
    "smua.source.func = smua.OUTPUT_DCVOLTS",
    "smua.source.autorangev = smua.AUTORANGE_ON",
    "smua.source.output = smua.OUTPUT_ON",
    
    "smua.source.levelv = 1.0",
    "delay(1)",                 # The instrument handles the 1s delay internally
    
    "smua.source.levelv = -1.0",
    "delay(1)",                 # The instrument handles the 1s delay internally
    
    "smua.source.output = smua.OUTPUT_OFF"
]

# Send the commands line by line to be executed immediately
for command in tsp_commands:
    keithley.write(command)

keithley.close()
print("Sequence executed internally by the Keithley.")