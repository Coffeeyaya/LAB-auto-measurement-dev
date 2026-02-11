import pyvisa
import time
import csv

# --- CONFIGURATION ---
# PASTE YOUR USB ID HERE:
RESOURCE_ID = "USB0::0x05E6::0x2636::4407529::INSTR"

FILENAME = "final_cycles.csv"
DRAIN_V = 1.0       
GATE_HIGH = 1.0     
GATE_LOW = -1.0     
POINTS_PER_PULSE = 30  # Adjust this for density (30 pts ~ 1 second)
CYCLES = 5             # How many +1/-1 loops to run

# --- CONNECT ---
rm = pyvisa.ResourceManager()
try:
    keithley = rm.open_resource(RESOURCE_ID)
    keithley.timeout = 20000 
    keithley.write_termination = '\n'
    keithley.read_termination = '\n'
    print(f"Connected: {keithley.query('*idn?').strip()}")
except:
    print("Connection Failed. Check USB ID.")
    exit()

print(f"--- STARTING {CYCLES} CYCLES ---")

try:
    # 1. SETUP (Fixed Range = Speed)
    keithley.write("abort; *rst; *cls")
    time.sleep(1.0)

    setup_cmds = [
        "format.data = format.ASCII",
        # Drain
        f"smua.source.func=smua.OUTPUT_DCVOLTS; smua.source.levelv={DRAIN_V}",
        "smua.source.limiti=0.1; smua.measure.rangei=0.1",
        "smua.measure.nplc=0.01; smua.measure.autorangei=0",
        "smua.source.output=1",
        # Gate
        f"smub.source.func=smua.OUTPUT_DCVOLTS; smub.source.levelv={GATE_LOW}",
        "smub.source.limiti=0.1; smub.measure.rangei=0.1",
        "smub.measure.nplc=0.01; smub.measure.autorangei=0",
        "smub.source.output=1"
    ]
    for cmd in setup_cmds: keithley.write(cmd)

    # 2. MAIN LOOP
    data_log = []
    start_time = time.time()

    for i in range(CYCLES):
        print(f"Cycle {i+1}/{CYCLES}...", end="", flush=True)
        
        # --- A. HIGH PULSE ---
        keithley.write(f"smub.source.levelv = {GATE_HIGH}")
        for _ in range(POINTS_PER_PULSE):
            try:
                keithley.write("print(smua.measure.i(), smub.measure.i())")
                resp = keithley.read().replace('\t', ',').split(',')
                if len(resp) >= 2:
                    data_log.append([time.time()-start_time, GATE_HIGH, float(resp[0]), float(resp[1])])
            except: pass
            
        # --- B. LOW PULSE ---
        keithley.write(f"smub.source.levelv = {GATE_LOW}")
        for _ in range(POINTS_PER_PULSE):
            try:
                keithley.write("print(smua.measure.i(), smub.measure.i())")
                resp = keithley.read().replace('\t', ',').split(',')
                if len(resp) >= 2:
                    data_log.append([time.time()-start_time, GATE_LOW, float(resp[0]), float(resp[1])])
            except: pass
        
        print(" Done.")

    # 3. SAVE
    print(f"Captured {len(data_log)} points.")
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        writer.writerows(data_log)
    print(f"Saved to {FILENAME}")

except Exception as e:
    print(f"Error: {e}")

finally:
    # 4. SAFETY SHUTDOWN (0V)
    print("Setting 0V and turning OFF...")
    try:
        keithley.write("smua.source.levelv = 0")
        keithley.write("smub.source.levelv = 0")
        time.sleep(0.5)
        keithley.write("smua.source.output = 0")
        keithley.write("smub.source.output = 0")
        keithley.close()
    except: pass