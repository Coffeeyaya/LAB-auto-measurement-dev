import pyvisa
import time

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
# Double check your address
keithley = rm.open_resource('GPIB0::26::INSTR') 

# === FIX 1: Set Timeout to 10 seconds (default is 2s, which is often too short) ===
keithley.timeout = 10000 

# === FIX 2: Define Termination Characters ===
# This tells Python: "Stop listening when you see a new line (\n)"
keithley.read_termination = '\n'
keithley.write_termination = '\n'

try:
    # === FIX 3: Force Abort & Clear ===
    print("Resetting instrument state...")
    keithley.write("abort")  # Stop any defined scripts running in the background
    keithley.write("*CLS")   # Clear the error queue history
    
    # Check connection
    idn = keithley.query("*IDN?")
    print(f"Connected successfully to: {idn.strip()}")

    # Check for hidden errors from previous attempts
    # The 2600B stores errors in an internal queue. Let's read it.
    error_count = int(float(keithley.query("print(errorqueue.count)")))
    if error_count > 0:
        print(f"WARNING: Found {error_count} old errors in the buffer:")
        for _ in range(error_count):
            err = keithley.query("print(errorqueue.next())")
            print(f"  -> {err.strip()}")
        keithley.write("errorqueue.clear()")
    else:
        print("No previous errors found.")

    # --- RUN THE TEST ---
    print("\nStarting simple measurement loop...")
    
    # Configure format
    keithley.write("format.data = format.ASCII")
    keithley.write("smua.reset()")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write("smua.source.levelv = 1.0")
    
    # Take 5 readings
    for i in range(5):
        # We query ONE thing at a time to be safe
        current_str = keithley.query("print(smua.measure.i())")
        print(f"Reading {i+1}: {current_str.strip()} A")
        time.sleep(0.5)

    print("\nSuccess! Communication is fixed.")

except pyvisa.VisaIOError as e:
    print("\nCRITICAL ERROR: Still timing out.")
    print("1. Check if the 'REM' (Remote) light is on.")
    print("2. Try turning the Keithley OFF and ON again.")
    print(f"Details: {e}")

finally:
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.close()