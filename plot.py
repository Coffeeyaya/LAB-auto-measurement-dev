import matplotlib.pyplot as plt
import time
import os

FILENAME = "live_measurements.csv"

# Setup Graph
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

line_id, = ax1.plot([], [], 'b-', linewidth=1, label='Drain Current')
line_ig, = ax2.plot([], [], 'r-', linewidth=1, label='Gate Current')

ax1.set_ylabel('Drain Current (A)')
ax1.set_title('Live Data Viewer (Reading CSV)')
ax1.grid(True); ax1.legend()

ax2.set_ylabel('Gate Current (A)')
ax2.set_xlabel('Time (s)')
ax2.grid(True); ax2.legend()

print("Waiting for data file...")

# Wait until file is created by the other script
while not os.path.exists(FILENAME):
    time.sleep(0.1)

print("File found! Plotting...")

last_pos = 0 # Keep track of where we read up to
times, id_data, ig_data = [], [], []

try:
    while True:
        with open(FILENAME, 'r') as f:
            # Jump to the last known position so we don't re-read old lines
            f.seek(last_pos)
            
            lines = f.readlines()
            
            # Save new position
            last_pos = f.tell()
            
            if not lines:
                # No new data yet, wait a bit
                plt.pause(0.1)
                continue
                
            for line in lines:
                try:
                    parts = line.strip().split(',')
                    # Skip header or incomplete lines
                    if parts[0] == "Time" or len(parts) < 4:
                        continue
                        
                    t = float(parts[0])
                    i_d = float(parts[2])
                    i_g = float(parts[3])
                    
                    times.append(t)
                    id_data.append(i_d)
                    ig_data.append(i_g)
                except ValueError:
                    continue
            
            # Update Plot if we have data
            if times:
                line_id.set_data(times, id_data)
                line_ig.set_data(times, ig_data)
                
                ax1.relim(); ax1.autoscale_view()
                ax2.relim(); ax2.autoscale_view()
                
                plt.pause(0.1) # Update rate (adjust as needed)

except KeyboardInterrupt:
    print("\nPlotter stopped.")