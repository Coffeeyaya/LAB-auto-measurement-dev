import pyvisa
import time
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0  # Volts
GATE_HIGH = 1.0      # Volts
GATE_LOW = -1.0      # Volts
STEP_DURATION = 1.0  # Seconds per step
TOTAL_CYCLES = 5     # How many times to flip-flop

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")  # your USB address

# Reset and Configure SMU A (DRAIN)
keithley.write("smua.reset()")
# Reset and Configure SMU B (gate)
keithley.write("smub.reset()")