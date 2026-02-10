import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
FILENAME = "simple_pulse_data.csv"
ERROR_LOG = "error_log.txt"
DRAIN_VOLTAGE = 1.0
GATE_VOLTAGE = 1.0
PULSE_WIDTH = 1.0

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000
keithley.read_termination = '\n'

def check_instrument_errors():
    """Queries the Keithley error queue and saves any messages."""
    try:
        # Ask how many errors are in the queue
        count = int(float(keithley.query("print(errorqueue.count)")))
        if count == 0:
            return False # No errors
        
        print(f"\n[!] FOUND {count} ERRORS. Saving to {ERROR_LOG}...")
        with open(ERROR_LOG, 'w') as f:
            f.write(f"Timestamp: {time.ctime()}\n")
            for i in range(count):
                # Get the error code and message
                err_msg = keithley.query("print(errorqueue.next())").strip()
                print(f"  -> {err_msg}")
                f.write(f"Error {i+1}: {err_msg}\n")
        return True # Errors found
    except Exception as e:
        print(f"Could not read error queue: {e}")
        return True

print("--- STARTING DIAGNOSTIC TEST ---")

try:
    # 1. HARD RESET
    keithley.write("abort")
    keithley.write("*cls")
    keithley.write("reset()")
    time.sleep(1) # Give it a moment to reset

    # 2. SETUP SMUs
    # We send these as simple, separate lines to avoid block syntax errors
    setup_cmds = [
        "smua.source.func = smua.OUTPUT_DCVOLTS",
        "smub.source.func = smua.OUTPUT_DCVOLTS",
        "smua.measure.nplc = 0.01",
        "smub.measure.nplc = 0.01",
        "smua.measure.autorangei = smua.AUTORANGE_ON",
        "smub.measure.autorangei = smua.AUTORANGE_ON",
        "display.screen = display.SMUA_SMUB",
        "format.data = format.ASCII"
    ]
    for cmd in setup_cmds:
        keithley.write(cmd)

    # Check for setup errors
    if check_instrument_errors():
        raise Exception("Setup Failed")

    # 3. CONFIGURE BUFFERS (LUA BLOCK)
    # We strip newlines and comments to make it a safe "one-liner"
    print("Configuring buffers...")
    
    # This is the Raw Lua Code
    lua_script = f"""
    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()
    smua.nvbuffer1.appendmode = 1
    smub.nvbuffer1.appendmode = 1
    
    smua.source.levelv = {DRAIN_VOLTAGE}
    smua.source.output = smua.OUTPUT_ON
    
    smub.source.levelv = {GATE_VOLTAGE}
    smub.source.output = smua.OUTPUT_ON
    
    timer.reset()
    start_t = timer.measure.t()
    while (timer.measure.t() - start_t) < {PULSE_WIDTH} do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
    end
    
    smua.source.output = smua.OUTPUT_OFF
    smub.source.output = smua.OUTPUT_OFF
    
    printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)
    printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)
    """
    
    # CRITICAL FIX: Send exactly what the instrument expects
    keithley.write(lua_script)

    # 4. WAIT FOR PULSE TO FINISH
    print("Pulse running...")
    time.sleep(PULSE_WIDTH + 1.0) # Wait 1s (pulse) + 1s (safety)

    # 5. CHECK FOR EXECUTION ERRORS
    if check_instrument_errors():
        raise Exception("Execution Failed - Check error_log.txt")

    # 6. READ DATA
    print("Reading data...")
    raw_id = keithley.read()
    raw_ig = keithley.read()

    # 7. SAVE DATA
    data_id = np.fromstring(raw_id, sep=',')
    data_ig = np.fromstring(raw_ig, sep=',')
    num_pts = len(data_id)
    times = np.linspace(0, PULSE_WIDTH, num_pts)

    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        for i in range(num_pts):
            writer.writerow([times[i], GATE_VOLTAGE, data_id[i], data_ig[i]])

    print(f"SUCCESS. Saved {num_pts} points to {FILENAME}")

except Exception as e:
    print(f"\nTEST ABORTED: {e}")
    # Run error check one last time just in case
    check_instrument_errors()

finally:
    keithley.close()