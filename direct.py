import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
FILENAME = "direct_pulse_data.csv"
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

print("--- STARTING DIRECT CONTROL TEST ---")

try:
    # 1. NUCLEAR RESET (Clear everything)
    # We send these one by one to make sure the instrument is listening
    keithley.write("abort")
    keithley.write("*rst")
    keithley.write("errorqueue.clear()")
    keithley.write("smua.reset()")
    keithley.write("smub.reset()")
    time.sleep(1.0) # Wait for reset to finish

    # 2. SETUP (Send commands line-by-line)
    # This avoids "Syntax Error at line 1" because we aren't sending a block.
    cmds = [
        "format.data = format.ASCII",
        "display.screen = display.SMUA_SMUB",
        
        # Setup SMU A (Drain)
        "smua.source.func = smua.OUTPUT_DCVOLTS",
        f"smua.source.levelv = {DRAIN_V}",
        "smua.source.output = smua.OUTPUT_ON",
        "smua.measure.nplc = 0.01",
        "smua.measure.autorangei = smua.AUTORANGE_ON",
        "smua.nvbuffer1.clear()",
        "smua.nvbuffer1.appendmode = 1",
        
        # Setup SMU B (Gate)
        "smub.source.func = smua.OUTPUT_DCVOLTS",
        f"smub.source.levelv = {GATE_V}",
        "smub.source.output = smua.OUTPUT_ON",
        "smub.measure.nplc = 0.01",
        "smub.measure.autorangei = smua.AUTORANGE_ON",
        "smub.nvbuffer1.clear()",
        "smub.nvbuffer1.appendmode = 1"
    ]

    print("Configuring instrument...")
    for cmd in cmds:
        keithley.write(cmd)

    # 3. RUN THE LOOP (The Magic Part)
    # We send the loop as a SINGLE, CLEAN STRING to avoid timing issues.
    print(f"Executing {PULSE_WIDTH}s pulse...")
    
    loop_code = f"""
    timer.reset()
    start_t = timer.measure.t()
    while (timer.measure.t() - start_t) < {PULSE_WIDTH} do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
    end
    print("DONE")
    """
    
    # Send the loop code
    keithley.write(loop_code)

    # 4. WAIT FOR "DONE"
    # We read continuously until we see "DONE". This ensures we stay in sync.
    response = keithley.read()
    if "DONE" not in response:
        print(f"Warning: Unexpected response '{response}'")

    # 5. DOWNLOAD DATA
    print("Downloading data...")
    
    # Get Drain Data
    keithley.write("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)")
    raw_id = keithley.read()
    
    # Get Gate Data
    keithley.write("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)")
    raw_ig = keithley.read()

    # 6. SAVE TO CSV
    data_id = np.fromstring(raw_id, sep=',')
    data_ig = np.fromstring(raw_ig, sep=',')
    num_pts = len(data_id)
    
    print(f"Captured {num_pts} points.")
    
    # Create Time Axis
    times = np.linspace(0, PULSE_WIDTH, num_pts)
    
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        for t, i_d, i_g in zip(times, data_id, data_ig):
            writer.writerow([t, GATE_V, i_d, i_g])
            
    print(f"SUCCESS! Saved to {FILENAME}")

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    # Force read error queue to see what happened
    try:
        print("Last Instrument Error:", keithley.query("print(errorqueue.next())"))
    except:
        pass

finally:
    # 7. SAFETY SHUTDOWN
    print("Shutting down...")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
    except:
        pass
    keithley.close()