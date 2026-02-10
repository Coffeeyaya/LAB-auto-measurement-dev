import pyvisa
import time

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0     # Volts
GATE_HIGH = 1.0         # Volts
GATE_LOW = -1.0         # Volts
CYCLES = 3              # How many loops to run
READINGS_PER_STEP = 5   # How many data points to print per voltage level

# --- CONNECT ---
rm = pyvisa.ResourceManager()
# Double check your address (GPIB0::26::INSTR or USB0::...)
keithley = rm.open_resource('GPIB0::26::INSTR')

print(f"Connected to: {keithley.query('*IDN?').strip()}")

try:
    # 1. SETUP
    # Set data format to ASCII so it is readable
    keithley.write("format.data = format.ASCII")
    
    # Configure Drain (SMUA)
    keithley.write("smua.reset()")
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")

    # Configure Gate (SMUB)
    keithley.write("smub.reset()")
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smub.source.output = smua.OUTPUT_ON")
    
    print("\n--- STARTING MEASUREMENT ---")
    print("Format: [Drain Current (A), Gate Current (A)]")

    for i in range(CYCLES):
        
        # --- STEP 1: GATE HIGH ---
        print(f"\n[Cycle {i+1}] Setting Gate to {GATE_HIGH} V")
        keithley.write(f"smub.source.levelv = {GATE_HIGH}")
        time.sleep(0.1) # Stabilization time
        
        for _ in range(READINGS_PER_STEP):
            # Query both currents
            # The 'print' command sends the string back to Python
            response = keithley.query("print(smua.measure.i(), smub.measure.i())")
            print(f"  High: {response.strip()}")
            time.sleep(0.2)

        # --- STEP 2: GATE LOW ---
        print(f"\n[Cycle {i+1}] Setting Gate to {GATE_LOW} V")
        keithley.write(f"smub.source.levelv = {GATE_LOW}")
        time.sleep(0.1) # Stabilization time
        
        for _ in range(READINGS_PER_STEP):
            response = keithley.query("print(smua.measure.i(), smub.measure.i())")
            print(f"  Low : {response.strip()}")
            time.sleep(0.2)

finally:
    # --- SAFETY SHUTDOWN ---
    print("\nTest finished. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()