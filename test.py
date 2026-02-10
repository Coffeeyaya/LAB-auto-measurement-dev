import pyvisa
import time
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0  # Volts
GATE_HIGH = 1.0      # Volts
GATE_LOW = -1.0      # Volts
STEP_DURATION = 1.0  # Seconds per step
TOTAL_CYCLES = 5     # How many times to flip-flop

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
# Replace with your actual address (e.g., 'GPIB0::26::INSTR' or 'USB0::...')
keithley = rm.open_resource('GPIB0::26::INSTR') 

# Reset and Configure SMU A (DRAIN)
keithley.write("smua.reset()")
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smua.source.output = smua.OUTPUT_ON")
keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}") # Set Drain to constant 1V

# Reset and Configure SMU B (GATE)
keithley.write("smub.reset()")
keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smub.source.output = smua.OUTPUT_ON")
keithley.write(f"smub.source.levelv = {GATE_HIGH}")   # Start at High

# --- SETUP PLOT ---
plt.ion() # Turn on interactive mode for real-time plotting
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))

# Data storage
times = []
id_data = [] # Drain Current
ig_data = [] # Gate Current
vg_data = [] # Gate Voltage (for reference)

# Plot Lines
line_id, = ax1.plot([], [], 'b-', label='Drain Current (Id)')
line_ig, = ax2.plot([], [], 'r-', label='Gate Current (Ig)')

ax1.set_ylabel('Drain Current (A)')
ax1.set_title(f'Real-Time Monitoring (Vd={DRAIN_VOLTAGE}V)')
ax1.grid(True)
ax1.legend(loc='upper right')

ax2.set_ylabel('Gate Current (A)')
ax2.set_xlabel('Time (s)')
ax2.grid(True)
ax2.legend(loc='upper right')

print("Starting measurement... Press Ctrl+C to stop early.")
start_time = time.time()

try:
    for cycle in range(TOTAL_CYCLES):
        # We alternate between High and Low states
        for gate_val in [GATE_HIGH, GATE_LOW]:
            
            # 1. Set the Gate Voltage
            keithley.write(f"smub.source.levelv = {gate_val}")
            step_start = time.time()
            
            # 2. Loop continuously during the "Step Duration" (1 second)
            while (time.time() - step_start) < STEP_DURATION:
                
                # Ask Keithley for both currents at once
                # We use the Lua print() command to send data back to PC
                response = keithley.query("print(smua.measure.i(), smub.measure.i())")
                
                # Parse the response (e.g., "1.23E-06\t4.5E-12")
                try:
                    vals = response.strip().split()
                    curr_drain = float(vals[0])
                    curr_gate = float(vals[1])
                    curr_time = time.time() - start_time
                    
                    # Store data
                    times.append(curr_time)
                    id_data.append(curr_drain)
                    ig_data.append(curr_gate)
                    vg_data.append(gate_val)
                    
                    # Update Plot (every few points to save CPU)
                    if len(times) % 5 == 0: 
                        line_id.set_data(times, id_data)
                        line_ig.set_data(times, ig_data)
                        
                        # Rescale axes to fit new data
                        ax1.relim()
                        ax1.autoscale_view()
                        ax2.relim()
                        ax2.autoscale_view()
                        
                        # Pause briefly to allow the plot to redraw
                        plt.pause(0.01)
                        
                except ValueError:
                    print(f"Read error: {response}")

finally:
    # --- SAFETY SHUTDOWN ---
    print("\nMeasurement finished. Turning off outputs.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()
    
    # Keep the plot open after the script finishes
    plt.ioff()
    plt.show()