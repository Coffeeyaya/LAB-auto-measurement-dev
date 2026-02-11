import pyvisa
import time
import csv
import numpy as np

# --- CONFIGURATION ---
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR" # Your ID
FILENAME = "usb_pulse_data.csv"
DRAIN_V = 1.0       # Volts
GATE_HIGH = 1.0     # Volts
GATE_LOW = -1.0     # Volts
PULSE_WIDTH = 1.0   # Seconds

# --- CONNECT ---
try:
    rm = pyvisa.ResourceManager()
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
    print(f"Connected to: {keithley.query('*idn?').strip()}")

except Exception as e:
    print(f"CONNECTION ERROR: {e}")
    exit()

print("--- STARTING ROBUST USB PULSE ---")

try:
    # 1. SETUP
    # Reset and Clear Errors
    keithley.write("abort")
    keithley.write("*rst")
    keithley.write("errorqueue.clear()")
    keithley.write("smua.reset()")
    keithley.write("smub.reset()")
    time.sleep(1.0) 

    # Setup SMU A (Drain)
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smua.source.levelv = {DRAIN_V}")
    keithley.write("smua.source.limiti = 0.1")  # Limit to 100mA to stop Overflow
    keithley.write("smua.measure.autorangei = 1")
    keithley.write("smua.source.output = 1")

    # Setup SMU B (Gate)
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smub.source.levelv = {GATE_LOW}")
    keithley.write("smub.source.limiti = 0.1")  # Limit to 100mA
    keithley.write("smub.measure.autorangei = 1")
    keithley.write("smub.source.output = 1")
    
    # 2. RUN PULSE
    print(f"Pulsing Gate to {GATE_HIGH}V...")
    
    data_log = []
    start_time = time.time()
    
    # A. Set High
    keithley.write(f"smub.source.levelv = {GATE_HIGH}")
    
    # B. Measure Loop
    pulse_start = time.time()
    while (time.time() - pulse_start) < PULSE_WIDTH:
        try:
            # Ask strictly for CURRENTS (2 values)
            # This is safer than asking for V and I
            keithley.write("print(smua.measure.i(), smub.measure.i())")
            
            # Read response
            response = keithley.read()
            
            # DEBUG: Uncomment this if it fails again to see raw data
            # print(f"Raw: {response.strip()}") 

            # Parse 2 values: Ia, Ib
            # We handle Tabs OR Commas to be safe
            clean_resp = response.replace('\t', ',')
            parts = clean_resp.split(',')
            
            if len(parts) >= 2:
                i_drain = float(parts[0])
                i_gate = float(parts[1])
                
                t_now = time.time() - start_time
                data_log.append([t_now, i_drain, i_gate])
            else:
                # If we get weird data, ignore this one point, don't crash
                continue

        except Exception as loop_err:
            # If "Overflow" or parsing fails, just print it and keep going
            print(f"Skipped point due to error: {loop_err}")

    # C. Set Low (Recovery)
    print(f"Returning Gate to {GATE_LOW}V...")
    keithley.write(f"smub.source.levelv = {GATE_LOW}")
    
    # 3. SAVE
    print(f"Captured {len(data_log)} points.")
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "I_Drain", "I_Gate"])
        writer.writerows(data_log)
        
    print(f"Saved to {FILENAME}")

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    # Read instrument error queue if possible
    try: print(f"Keithley Error: {keithley.query('print(errorqueue.next())')}")
    except: pass

finally:
    print("Shutting down.")
    try:
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except:
        pass