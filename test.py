import pyvisa
import time
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
DRAIN_VOLTAGE = 1.0   # Volts
GATE_HIGH = 1.0       # Volts
GATE_LOW = -1.0       # Volts
TOTAL_CYCLES = 3      # Number of loops
POINTS_PER_STEP = 10  # How many data points to take per voltage level

# --- SETUP INSTRUMENT ---
rm = pyvisa.ResourceManager()
# Use your specific address
keithley = rm.open_resource('GPIB0::26::INSTR') 

# 1. IMPORTANT: Force data format to be simple ASCII text
keithley.write("format.data = format.ASCII")

# 2. Reset and Configure SMU A (DRAIN)
keithley.write("smua.reset()")
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smua.source.output = smua.OUTPUT_ON")
keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")

# 3. Reset and Configure SMU B (GATE)
keithley.write("smub.reset()")
keithley.write("smub.source.func = smua.OUTPUT_DCVOLTS")
keithley.write("smub.source.output = smua.OUTPUT_ON")
keithley.write(f"smub.source.levelv = {GATE_HIGH}") 

# --- SETUP PLOT ---
plt.ion() # Interactive mode ON
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# Lists to hold the data
t_list = []
id_list = []
ig_list = []

# Initialize the lines
line_id, = ax1.plot([], [], 'b.-', label='Drain Current (Id)')
line_ig, = ax2.plot([], [], 'r.-', label='Gate Current (Ig)')

ax1.set_ylabel('Drain Current (A)')
ax1.set_title('Real-Time Monitor')
ax1.grid(True)
ax1.legend()

ax2.set_ylabel('Gate Current (A)')
ax2.set_xlabel('Time (s)')
ax2.grid(True)
ax2.legend()

print("Starting... Check terminal for raw data values.")
start_time = time.time()

try:
    for cycle in range(TOTAL_CYCLES):
        for gate_val in [GATE_HIGH, GATE_LOW]:
            
            # Switch Voltage
            keithley.write(f"smub.source.levelv = {gate_val}")
            print(f"\n--- Switched Gate to {gate_val} V ---")
            
            # Take measurements for this step
            for _ in range(POINTS_PER_STEP):
                
                # Request data
                # We use reading buffers to get a clean spot reading
                raw_data = keithley.query("print(smua.measure.i(), smub.measure.i())")
                
                # --- DEBUG PRINT: See what the instrument is actually saying ---
                print(f"Raw from Keithley: {raw_data.strip()}") 
                
                try:
                    # Clean up the string and split
                    parts = raw_data.strip().split()
                    curr_drain = float(parts[0])
                    curr_gate = float(parts[1])
                    curr_time = time.time() - start_time
                    
                    # Append to lists
                    t_list.append(curr_time)
                    id_list.append(curr_drain)
                    ig_list.append(curr_gate)
                    
                    # Update plot data
                    line_id.set_data(t_list, id_list)
                    line_ig.set_data(t_list, ig_list)
                    
                    # Force axis to rescale to new data
                    ax1.relim()
                    ax1.autoscale_view()
                    ax2.relim()
                    ax2.autoscale_view()
                    
                    # Tiny pause to let the GUI event loop catch up
                    plt.pause(0.05)
                    
                except Exception as e:
                    print(f"Error parsing data: {e}")

finally:
    print("\nScript finished. Turning off outputs.")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()
    
    # Keep plot open at the end
    plt.ioff()
    plt.show()