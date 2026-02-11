import pyvisa

# Connect to the instrument (update the resource string for your setup)
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")  # replace with your IP or GPIB

# Enable TSP scripting mode
keithley.write("smua.reset()")
keithley.write("smub.reset()")

# Set source voltage
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smua.source.levelv = 1")   # SMUA = 1 V
keithley.write("smua.source.output = smua.OUTPUT_ON")

keithley.write("smub.source.func = smub.OUTPUT_DCVOLTS")
keithley.write("smub.source.levelv = 1")   # SMUB = 1 V
keithley.write("smub.source.output = smub.OUTPUT_ON")

# Measure current from both channels
i_a = keithley.query("print(smua.measure.i())")
i_b = keithley.query("print(smub.measure.i())")

print(f"Current SMUA: {i_a} A")
print(f"Current SMUB: {i_b} A")

# Turn off outputs
keithley.write("smua.source.output = smua.OUTPUT_OFF")
keithley.write("smub.source.output = smub.OUTPUT_OFF")
