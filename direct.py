import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
FILENAME = "final_pulse_data.csv"
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

print("--- STARTING ONE-LINER TEST ---")

try:
    # 1. SETUP (Send simple commands line-by-line)
    # We set up the buffers and source settings first.
    print("Configuring instrument...")
    keithley.write("abort")
    keithley.write("*rst") 
    keithley.write("errorqueue.clear()")
    time.sleep(0.5)

    setup_cmds = [
        "display.screen = display.SMUA_SMUB",
        "format.data = format.ASCII",
        
        # SMU A (Drain) Setup
        "smua.source.func = smua.OUTPUT_DCVOLTS",
        f"smua.source.levelv = {DRAIN_V}",
        "smua.source.output = smua.OUTPUT_ON",
        "smua.measure.nplc = 0.01",
        "smua.measure.autorangei = smua.AUTORANGE_ON",
        "smua.nvbuffer1.clear()",
        "smua.nvbuffer1.appendmode = 1",
        
        # SMU B (Gate) Setup
        "smub.source.func = smua.OUTPUT_DCVOLTS",
        f"smub.source.levelv = {GATE_V}",
        "smub.source.output = smua.OUTPUT_ON",
        "smub.measure.nplc = 0.01",
        "smub.measure.autorangei = smua.AUTORANGE_ON",
        "smub.nvbuffer1.clear()",
        "smub.nvbuffer1.appendmode = 1"
    ]

    for cmd in setup_cmds:
        keithley.write(cmd)
        time.sleep(0.01) # Tiny safety delay

    # 2. THE ONE-LINER (The Fix)
    # We condense the entire 'while' loop into a single string.
    # Lua allows this as long as we separate commands with spaces.
    # There are NO newlines here, so the Keithley sees it as one command.
    print(f"Sending {PULSE_WIDTH}s pulse...")
    
    one_liner = (
        f"timer.reset() "
        f"start_t = timer.measure.t() "
        f"while (timer.measure.t() - start_t) < {PULSE_WIDTH} do "
        f"smua.measure.i(smua.nvbuffer1) "
        f"smub.measure.i(smub.nvbuffer1) "
        f"end "
        f"print('DONE')"
    )
    
    # Send it!
    keithley.write(one_liner)

    # 3. WAIT & SYNC
    # Read until we see "DONE"
    response = keithley.read()
    if "DONE" not in response:
        print(f"Warning: Expected 'DONE', got '{response}'")

    # 4. DOWNLOAD DATA
    print("Downloading data...")
    keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
    raw_id = keithley.read()
    
    keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
    raw_ig = keithley.read()

    # 5. SAVE
    data_id = np.fromstring(raw_id, sep=',')
    data_ig = np.fromstring(raw_ig, sep=',')
    num_pts = len(data_id)
    print(f"Captured {num_pts} points.")
    
    times = np.linspace(0, PULSE_WIDTH, num_pts)
    
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        for t, i_d, i_g in zip(times, data_id, data_ig):
            writer.writerow([t, GATE_V, i_d, i_g])
            
    print(f"SUCCESS! Saved to {FILENAME}")

except Exception as e:
    print(f"\nERROR: {e}")
    try: print("Instrument Error:", keithley.query("print(errorqueue.next())"))
    except: pass

finally:
    print("Resetting to 0V...")
    keithley.write("smua.source.output = 0")
    keithley.write("smub.source.output = 0")
    keithley.close()