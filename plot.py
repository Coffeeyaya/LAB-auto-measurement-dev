import matplotlib.pyplot as plt
import time
import os

FILENAME = "buffer_data.csv"

# --- PLOT SETUP ---
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Use small markers '.' to see individual points
line_id, = ax1.plot([], [], 'b.-', markersize=2, label='Drain Current')
line_ig, = ax2.plot([], [], 'r.-', markersize=2, label='Gate Current')

ax1.set_ylabel('Drain Current (A)')
ax1.set_title('Live Buffer Plot (Updating every 1s)')
ax1.grid(True)
ax1.legend(loc='upper right')

ax2.set_ylabel('Gate Current (A)')
ax2.set_xlabel('Time (s)')
ax2.grid(True)
ax2.legend(loc='upper right')

print("Waiting for data file...")
while not os.path.exists(FILENAME):
    time.sleep(0.1)

print("File found! Plotting...")

last_pos = 0
times, id_data, ig_data = [], [], []

try:
    while True:
        with open(FILENAME, 'r') as f:
            f.seek(last_pos)
            lines = f.readlines()
            last_pos = f.tell()
            
            if not lines:
                plt.pause(0.1)
                continue
            
            new_data_found = False
            for line in lines:
                try:
                    parts = line.strip().split(',')
                    if parts[0] == "Time" or len(parts) < 4: continue
                    
                    times.append(float(parts[0]))
                    id_data.append(float(parts[2]))
                    ig_data.append(float(parts[3]))
                    new_data_found = True
                except ValueError:
                    continue
            
            if new_data_found:
                # Update Plot
                line_id.set_data(times, id_data)
                line_ig.set_data(times, ig_data)
                
                ax1.relim()
                ax1.autoscale_view()
                ax2.relim()
                ax2.autoscale_view()
                
                plt.pause(0.01)

except KeyboardInterrupt:
    print("Plotter stopped.")