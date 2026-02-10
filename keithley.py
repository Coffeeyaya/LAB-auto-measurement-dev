import pyvisa
import time
import matplotlib.pyplot as plt
import csv
from datetime import datetime

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0     # Volts (SMUA)
GATE_HIGH = 1.0         # Volts (SMUB)
GATE_LOW = -1.0         # Volts (SMUB)
CYCLES = 3              # Number of High/Low cycles
POINTS_PER_STEP = 10    # Data points per voltage level
FILENAME = f"keithley_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('GPIB0::26::INSTR') 

# CRITICAL SETTINGS (The "Fixes")
keithley.timeout = 10000                 # 10 seconds timeout
keithley.read_termination = '\n'         # Stop reading at new line
keithley.write_termination = '\n'        # Send new line at end of commands

# --- SETUP PLOT ---
plt.ion() # Interactive Mode
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Data Containers
times, v_gate, i_drain, i_gate = [], [], [], []

# Plot Lines
line_id, = ax1.plot([], [], 'b.-', label='Drain Current (Id)')
line_ig, = ax2.plot([], [], 'r.-', label='Gate Current (Ig)')

# Formatting
ax1.set_ylabel('Drain Current (A)')
ax1.set_title(f'Real-Time Pulse Measurement (Vd={DRAIN_VOLTAGE}V)')
ax1.grid(True)
ax1.legend()

ax2.set_ylabel('Gate Current (A)')
ax2.set_xlabel('Time (s)')
ax2.grid(True)
ax2.legend()

print(f"--- STARTING TEST ---")
print(f"Data will be saved to: {FILENAME}")

try:
    # 1. INITIALIZE HARDWARE
    keithley.write("abort")                  # Stop any background scripts
    keithley.write("*CLS")                   # Clear errors
    keithley.write("format.data = format.ASCII") # Simple text format
    
    # Configure SMUA (Drain)
    keithley.write("smua.reset()")
    keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smua.source.output = smua.OUTPUT_ON")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")

    # Configure SMUB (Gate)
    keithley.write("smub.reset()")
    keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write("smub.source.output = smua.OUTPUT_ON")
    keithley.write(f"smub.source.levelv = {GATE_HIGH}") # Start High

    # Open CSV file
    with open(FILENAME, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Time_s", "V_Gate_V", "I_Drain_A", "I_Gate_A"]) # Header

        start_time = time.time()

        # 2. MEASUREMENT LOOP
        for cycle in range(CYCLES):
            for voltage_step in [GATE_HIGH, GATE_LOW]:
                
                # Apply Voltage
                print(f"Setting Gate: {voltage_step} V")
                keithley.write(f"smub.source.levelv = {voltage_step}")
                
                # Display on Keithley Screen (Cool Trick!)
                keithley.write(f'display.smua.measure.func = display.MEASURE_DCAMPS')
                keithley.write(f'display.settext("Gate: {voltage_step} V")')
                
                # Take Measurements
                for _ in range(POINTS_PER_STEP):
                    # Query measurements
                    raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                    
                    try:
                        # Parse Data
                        vals = raw.strip().split()
                        t_now = time.time() - start_time
                        id_val = float(vals[0])
                        ig_val = float(vals[1])
                        
                        # Store Data
                        times.append(t_now)
                        v_gate.append(voltage_step)
                        i_drain.append(id_val)
                        i_gate.append(ig_val)
                        
                        # Write to CSV immediately (safe against crashes)
                        writer.writerow([t_now, voltage_step, id_val, ig_val])

                        # Update Plot
                        line_id.set_data(times, i_drain)
                        line_ig.set_data(times, i_gate)
                        
                        # Rescale Axes
                        ax1.relim()
                        ax1.autoscale_view()
                        ax2.relim()
                        ax2.autoscale_view()
                        
                        # Draw
                        plt.pause(0.01)
                        
                    except ValueError:
                        print(f"Skipping bad data point: {raw}")

finally:
    # 3. SAFETY SHUTDOWN
    print("\nTest Complete. Turning outputs OFF.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.write('display.clear()') # Clear the text message
    keithley.close()
    
    # Keep plot open
    plt.ioff()
    plt.show()