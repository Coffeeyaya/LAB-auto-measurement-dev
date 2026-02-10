import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
FILENAME = "atomic_pulse.csv"
DRAIN_V = 1.0       # Volts
GATE_V = 1.0        # Volts
PULSE_WIDTH = 1.0   # Seconds
TIMEOUT = 25000     # ms

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = TIMEOUT
keithley.write_termination = '\n'
keithley.read_termination = '\n'

print("--- ATOMIC PULSE TEST ---")

try:
    # 1. RESET (Clear state)
    keithley.write("abort; *rst; errorqueue.clear()")
    time.sleep(1.0)
    
    # 2. CONFIGURE DISPLAY & FORMAT
    keithley.write("display.screen = display.SMUA_SMUB")
    keithley.write("format.data = format.ASCII")

    # 3. THE "ATOMIC" COMMAND
    # We pack the Buffer Setup AND the Measurement Loop into one line.
    # This ensures 'Append Mode' is definitely ON when the loop runs.
    print(f"Executing {PULSE_WIDTH}s pulse...")

    atomic_script = (
        # --- A. Setup Buffers (Capacity & Mode) ---
        "smua.nvbuffer1.capacity = 10000 "
        "smub.nvbuffer1.capacity = 10000 "
        "smua.nvbuffer1.appendmode = 1 "  # CRITICAL: Append Mode ON
        "smub.nvbuffer1.appendmode = 1 "
        "smua.nvbuffer1.clear() "
        "smub.nvbuffer1.clear() "
        
        # --- B. Setup Source & Measure ---
        "smua.source.func = smua.OUTPUT_DCVOLTS "
        "smub.source.func = smua.OUTPUT_DCVOLTS "
        f"smua.source.levelv = {DRAIN_V} "
        f"smub.source.levelv = {GATE_V} "
        "smua.measure.nplc = 0.01 "       # Fast Speed
        "smub.measure.nplc = 0.01 "
        "smua.measure.autorangei = smua.AUTORANGE_ON "
        "smub.measure.autorangei = smua.AUTORANGE_ON "
        "smua.source.output = smua.OUTPUT_ON "
        "smub.source.output = smua.OUTPUT_ON "
        
        # --- C. The Loop ---
        "timer.reset() "
        "start_t = timer.measure.t() "
        f"while (timer.measure.t() - start_t) < {PULSE_WIDTH} do "
            "smua.measure.i(smua.nvbuffer1) "
            "smub.measure.i(smub.nvbuffer1) "
        "end "
        
        # --- D. Finish ---
        "smua.source.output = smua.OUTPUT_OFF "
        "smub.source.output = smua.OUTPUT_OFF "
        "print('DONE')"
    )

    # Send it all at once
    keithley.write(atomic_script)

    # 4. WAIT FOR "DONE"
    # This confirms the loop actually finished
    response = keithley.read()
    if "DONE" not in response:
        print(f"Warning: Expected 'DONE', got '{response}'")

    # 5. RETRIEVE DATA
    print("Downloading data...")
    
    # Get Counts
    count_a = int(float(keithley.query("print(smua.nvbuffer1.n)")))
    print(f"Points captured: {count_a}")
    
    if count_a > 1:
        # Download Buffers
        keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
        raw_id = keithley.read()
        
        keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
        raw_ig = keithley.read()

        # Save to CSV
        data_id = np.fromstring(raw_id, sep=',')
        data_ig = np.fromstring(raw_ig, sep=',')
        times = np.linspace(0, PULSE_WIDTH, count_a)
        
        with open(FILENAME, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
            for t, i_d, i_g in zip(times, data_id, data_ig):
                writer.writerow([t, GATE_V, i_d, i_g])
                
        print(f"SUCCESS! Saved to {FILENAME}")
        
    else:
        print("[!] Still captured only 1 point. Check if NPLC is too slow or Auto-Range is stuck.")
        # Debug: Print the one point
        print(f"Value: {keithley.query('print(smua.nvbuffer1[1])')}")

except Exception as e:
    print(f"\nERROR: {e}")
    try: print("Instrument Error:", keithley.query("print(errorqueue.next())"))
    except: pass

finally:
    keithley.close()