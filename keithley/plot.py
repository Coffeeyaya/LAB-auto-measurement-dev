'''
test keithley version 2
run with keithley.py
combined to run.bat
'''
import matplotlib.pyplot as plt
import pandas as pd
import time
import os

FILENAME = "shared_data.csv"

# Setup Plot
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Initial empty lines
line_id, = ax1.plot([], [], 'b.-', label='Drain Current')
line_ig, = ax2.plot([], [], 'r.-', label='Gate Current')

ax1.set_ylabel('Drain Current (A)'); ax1.legend(loc='upper right')
ax1.grid(True)
ax2.set_ylabel('Gate Current (A)'); ax2.legend(loc='upper right')
ax2.set_xlabel('Time (s)'); ax2.grid(True)

print("Waiting for data file...")

# Wait for file to be created
while not os.path.exists(FILENAME):
    time.sleep(0.1)

print("Plotting started!")

last_pos = 0 # Track how many lines we have read

while True:
    try:
        # Read the file effectively
        # Note: In a real heavy app, we would just read new lines.
        # Here, pandas is fast enough to read the whole file for < 1000 points.
        df = pd.read_csv(FILENAME)
        
        if not df.empty:
            # Update Data
            line_id.set_data(df['Time'], df['I_Drain'])
            line_ig.set_data(df['Time'], df['I_Gate'])
            
            # Auto-Scale Axes
            ax1.relim(); ax1.autoscale_view()
            ax2.relim(); ax2.autoscale_view()
            
            # Refresh
            plt.pause(0.5) # Update twice a second (saves CPU)
            
    except Exception as e:
        # File might be locked by writer for a millisecond, just ignore and try again
        pass
    
    time.sleep(0.1)