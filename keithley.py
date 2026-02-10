import pyvisa
import time
import matplotlib.pyplot as plt
import csv
from datetime import datetime

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0      # Volts
GATE_HIGH = 1.0          # Volts
GATE_LOW = -1.0          # Volts
PULSE_WIDTH = 1.0        # Exact duration for each step (Seconds)
TOTAL_CYCLES = 3         # How many loops
FILENAME = f"keithley_time_controlled_{datetime.now().strftime('%H%M%S')}.csv"

# --- CONNECT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR') 

# Critical Stability Settings
keithley.timeout = 10000 
keithley.read_termination = '\n'
keithley.write_termination = '\n'

# --- PLOT SETUP ---
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
times, i_drain, i_gate = [], [], []
line_id, = ax1.plot([], [], 'b.-', label='Id')
line_ig, = ax2.plot([], [], 'r.-', label='Ig')

ax1.set_ylabel('Drain Current (A)')
ax1.set_title(f'Precise Time Control (Pulse Width = {PULSE_WIDTH}s)')
ax1.grid(True)
ax2.set_ylabel('Gate Current (A)')
ax2.grid(True)

print(f"--- STARTING PRECISION TIMING TEST ---")
print(f"Voltage will switch exactly every {PULSE_WIDTH} seconds.")

try:
    # Init Hardware
    keithley.write("abort; *cls")
    keithley.write("format.data = format.ASCII")
    keithley.write("smua.reset(); smua.source.output = smua.OUTPUT_ON")
    keithley.write("smub.reset(); smub.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")

    start_exp = time.time()

    with open(FILENAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V_Gate", "I_Drain", "I_Gate"])

        for cycle in range(TOTAL_CYCLES):
            for v_gate in [GATE_HIGH, GATE_LOW]:
                
                # 1. Set Voltage
                keithley.write(f"smub.source.levelv = {v_gate}")
                print(f"Gate -> {v_gate} V")
                
                # 2. Start the Timer for this step
                step_start = time.time()
                
                # 3. Measure continuously until the PULSE_WIDTH time is up
                while (time.time() - step_start) < PULSE_WIDTH:
                    
                    # Measure
                    raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                    vals = raw.strip().split()
                    
                    # Record Time
                    t_now = time.time() - start_exp
                    
                    # Save & Plot
                    try:
                        id_val, ig_val = float(vals[0]), float(vals[1])
                        times.append(t_now)
                        i_drain.append(id_val)
                        i_gate.append(ig_val)
                        writer.writerow([t_now, v_gate, id_val, ig_val])
                        
                        # Update Plot (Only every 3rd point to save CPU and increase accuracy)
                        if len(times) % 3 == 0:
                            line_id.set_data(times, i_drain)
                            line_ig.set_data(times, i_gate)
                            ax1.relim(); ax1.autoscale_view()
                            ax2.relim(); ax2.autoscale_view()
                            plt.pause(0.001) # Minimum pause
                            
                    except ValueError:
                        pass

finally:
    print("Test Complete.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()
    plt.ioff(); plt.show()