import pyvisa
import time

# --- CONFIG ---
DRAIN_V = 1.0
GATE_V = 1.0
PULSE_WIDTH = 1.0

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 
keithley.write_termination = '\n'
keithley.read_termination = '\n'

print("--- DIAGNOSTIC RUN ---")

try:
    # 1. RESET
    print("Resetting instrument...")
    keithley.write("abort; *rst; errorqueue.clear()")
    time.sleep(1.0)

    # 2. DEFINE SCRIPT WITH DEBUG PRINTS
    # We define the function in Python to ensure it's perfect (no file errors)
    tsp_code = [
        "function DebugPulse()",
        "    print('Step 1: Function Started')",
        
        "    -- Test SMU A",
        "    if smua == nil then print('Error: SMU A not found') exit() end",
        "    smua.reset()",
        "    smua.source.func = smua.OUTPUT_DCVOLTS",
        "    print('Step 2: SMU A OK')",
        
        "    -- Test SMU B",
        "    if smub == nil then print('Error: SMU B not found') exit() end",
        "    smub.reset()",
        "    smub.source.func = smua.OUTPUT_DCVOLTS",
        "    print('Step 3: SMU B OK')",
        
        "    -- Test Buffers",
        "    smua.nvbuffer1.clear()",
        "    smub.nvbuffer1.clear()",
        "    print('Step 4: Buffers Cleared')",
        
        "    -- Configure Source",
        "    smua.source.levelv = 1.0",
        "    smub.source.levelv = 1.0",
        "    smua.source.output = smua.OUTPUT_ON",
        "    smub.source.output = smua.OUTPUT_ON",
        "    print('Step 5: Outputs ON')",
        
        "    -- Run brief pulse",
        "    delay(0.5)",
        
        "    -- Turn Off",
        "    smua.source.output = smua.OUTPUT_OFF",
        "    smub.source.output = smub.OUTPUT_OFF",
        "    print('Step 6: Success')",
        "end"
    ]
    
    # 3. UPLOAD SCRIPT
    print("Uploading debug script...")
    for line in tsp_code:
        keithley.write(line)
        time.sleep(0.05) # Tiny delay for safety

    # 4. RUN SCRIPT
    print("Executing DebugPulse()...")
    keithley.write("DebugPulse()")
    
    # 5. READ DEBUG OUTPUT
    # We read lines until we see 'Success' or an error happens
    print("\n--- KEITHLEY LOG ---")
    start_time = time.time()
    while (time.time() - start_time) < 5.0:
        try:
            # Read line from Keithley
            msg = keithley.read()
            print(f"Instrument: {msg}")
            if "Success" in msg:
                break
        except:
            # If read times out, loop again
            pass
            
    # Check for actual errors in the queue
    err_count = int(float(keithley.query("print(errorqueue.count)")))
    if err_count > 0:
        print("\n[!] ERRORS FOUND:")
        while err_count > 0:
            print(keithley.query("print(errorqueue.next())"))
            err_count -= 1

except Exception as e:
    print(f"\nPython Error: {e}")

finally:
    keithley.close()