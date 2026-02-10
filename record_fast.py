import pyvisa
import time
import matplotlib.pyplot as plt
import csv
import numpy as np

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0     # Volts
GATE_HIGH = 1.0         # Volts
GATE_LOW = -1.0         # Volts
PULSE_WIDTH = 1.0       # Seconds (Precision controlled by Keithley)
TOTAL_CYCLES = 5        # How many loops
FILENAME = "burst_data.csv"

# --- TSP SCRIPT (The Magic Part) ---
# We define a function inside the Keithley's memory.
# This loop runs INSIDE the instrument, so it is extremely fast.
tsp_script = """
function MeasurePulse(gate_volts, duration)
    -- 1. Setup Buffers
    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()
    smua.nvbuffer1.appendmode = 1
    smub.nvbuffer1.appendmode = 1
    
    -- 2. Set Voltage
    smub.source.levelv = gate_volts
    
    -- 3. Reset Timer
    timer.reset()
    start_t = timer.measure.t()
    
    -- 4. Fast Measurement Loop
    -- We loop until the 'timer' says 'duration' has passed.
    while (timer.measure.t() - start_t) < duration do
        smua.measure.i(smua.nvbuffer1) -- Measure Drain -> Store in Buffer A
        smub.measure.i(smub.nvbuffer1) -- Measure Gate  -> Store in Buffer B
    end
    
    -- 5. Send Data back to PC
    -- Format: DrainCurrent1, DrainCurrent2, ... GateCurrent1, GateCurrent2, ...
    printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)
    printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)
end
"""

# --- PYTHON SETUP ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR')
keithley.timeout = 20000 # Large timeout because we wait 1s for the pulse
keithley.read_termination = '\n'

# Initialize Plot
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
ax1.set_title('High-Speed Buffer Acquisition'); ax1.set_ylabel('Drain I (A)'); ax1.grid(True)
ax2.set_ylabel('Gate I (A)'); ax2.set_xlabel('Time (s)'); ax2.grid(True)
line_id, = ax1.plot([], [], 'b.-', markersize=2)
line_ig, = ax2.plot([], [], 'r.-', markersize=2)

# Global Data Containers
all_times, all_id, all_ig = [], [], []

print("--- STARTING BURST MODE MEASUREMENT ---")

try:
    # 1. SETUP INSTRUMENT
    keithley.write("abort; *cls")
    keithley.write("loadscript MyPulseFunc\n" + tsp_script + "\nendscript")
    keithley.write("MyPulseFunc.save()")  # Save it so we can call it
    
    # Configure Display & Auto-Range (As you requested)
    keithley.write("display.screen = display.SMUA_SMUB")
    keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON")
    keithley.write("smub.measure.autorangei = smua.AUTORANGE_ON")
    keithley.write("smua.measure.nplc = 0.01") # Fast measurements
    keithley.write("smub.measure.nplc = 0.01")

    # Turn Outputs ON
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write("smub.source.output = smua.OUTPUT_ON")

    # 2. RUN EXPERIMENT
    global_start_time = time.time()
    
    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])
        
        for cycle in range(TOTAL_CYCLES):
            for v_gate in [GATE_HIGH, GATE_LOW]:
                
                print(f"Cycle {cycle}: Pulsing {v_gate}V for {PULSE_WIDTH}s... ", end="", flush=True)
                
                # --- EXECUTE THE BURST ---
                # This single command triggers the 1-second loop inside the Keithley
                keithley.write(f"MeasurePulse({v_gate}, {PULSE_WIDTH})")
                
                # --- RETRIEVE DATA ---
                # We read two long strings of comma-separated numbers
                raw_id = keithley.read() # Read Drain Buffer
                raw_ig = keithley.read() # Read Gate Buffer
                
                # Convert string "1.2e-6, 1.3e-6..." to numpy array
                data_id = np.fromstring(raw_id, sep=',')
                data_ig = np.fromstring(raw_ig, sep=',')
                
                # Generate Timestamps for this chunk
                # We assume points are equally spaced over the pulse width
                num_points = len(data_id)
                chunk_times = np.linspace(0, PULSE_WIDTH, num_points) + (time.time() - global_start_time - PULSE_WIDTH)
                
                print(f"Captured {num_points} points.")
                
                # Save to Lists & CSV
                all_times.extend(chunk_times)
                all_id.extend(data_id)
                all_ig.extend(data_ig)
                
                for t, i_d, i_g in zip(chunk_times, data_id, data_ig):
                    writer.writerow([t, v_gate, i_d, i_g])
                f.flush()
                
                # Update Plot (Once per second, very efficient)
                line_id.set_data(all_times, all_id)
                line_ig.set_data(all_times, all_ig)
                ax1.relim(); ax1.autoscale_view()
                ax2.relim(); ax2.autoscale_view()
                plt.pause(0.01)

finally:
    print("Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()
    plt.ioff(); plt.show()