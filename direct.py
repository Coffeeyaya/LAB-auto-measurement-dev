import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
FILENAME = "safe_pulse_data.csv"
DRAIN_V = 1.0       
GATE_V = 1.0        
PULSE_WIDTH = 1.0   

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 25000 
keithley.write_termination = '\n'
keithley.read_termination = '\n'

print("--- STARTING SAFE MODE PULSE ---")

try:
    # 1. HARD RESET (The most important step)
    # We reset the SMUs individually to force them to factory defaults.
    # This clears all weird buffer settings causing your error.
    print("Resetting instrument...")
    keithley.write("abort")
    keithley.write("errorqueue.clear()")
    keithley.write("smua.reset()")
    keithley.write("smub.reset()")
    keithley.write("format.data = format.ASCII")
    
    # CRITICAL: Wait for reset to finish
    time.sleep(2.0)

    # 2. THE ONE-LINER (Simplicity = Success)
    # We do NOT resize capacity. We do NOT set append mode.
    # We just set the speed (NPLC), Clear, and Go.
    print(f"Executing {PULSE_WIDTH}s pulse...")

    # This string has NO newlines. It is one solid command.
    safe_script = (
        # Setup Speed
        "smua.measure.nplc=0.01 "
        "smub.measure.nplc=0.01 "
        "smua.measure.autorangei=1 "
        "smub.measure.autorangei=1 "
        
        # Clear Buffers (Default size is fine!)
        "smua.nvbuffer1.clear() "
        "smub.nvbuffer1.clear() "
        
        # Setup Source
        "smua.source.func=smua.OUTPUT_DCVOLTS "
        "smub.source.func=smua.OUTPUT_DCVOLTS "
        f"smua.source.levelv={DRAIN_V} "
        f"smub.source.levelv={GATE_V} "
        "smua.source.output=1 "
        "smub.source.output=1 "
        
        # Run Loop
        "timer.reset() "
        "st=timer.measure.t() "
        f"while (timer.measure.t()-st)<{PULSE_WIDTH} do "
            "smua.measure.i(smua.nvbuffer1) "
            "smub.measure.i(smub.nvbuffer1) "
        "end "
        
        # Stop
        "smua.source.output=0 "
        "smub.source.output=0 "
        "print('DONE')"
    )

    # Send command
    keithley.write(safe_script)

    # 3. WAIT FOR COMPLETION
    # We read until we get "DONE".
    response = keithley.read()
    if "DONE" not in response:
        print(f"Warning: Unexpected response '{response}'")

    # 4. DOWNLOAD
    print("Downloading data...")
    
    # Check count first
    count = int(float(keithley.query("print(smua.nvbuffer1.n)")))
    print(f"Captured {count} points.")
    
    if count > 0:
        keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
        raw_id = keithley.read()
        keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
        raw_ig = keithley.read()

        # Save
        data_id = np.fromstring(raw_id, sep=',')
        data_ig = np.fromstring(raw_ig, sep=',')
        times = np.linspace(0, PULSE_WIDTH, count)
        
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
            for t, id_val, ig_val in zip(times, data_id, data_ig):
                writer.writerow([t, GATE_V, id_val, ig_val])
        print(f"Saved to {FILENAME}")
    else:
        print("Buffer is empty!")

except Exception as e:
    print(f"\nERROR: {e}")
    # If this fails, the error queue will tell us the EXACT cause
    try: print("Instrument Error:", keithley.query("print(errorqueue.next())"))
    except: pass

finally:
    keithley.close()