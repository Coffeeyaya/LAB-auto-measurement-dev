'''
thread programming basics
'''
import threading
import queue
import time
import random
import matplotlib.pyplot as plt

# -------------------------
# Shared Objects
# -------------------------

stop_event = threading.Event()
data_queue = queue.Queue()
lock = threading.Lock()

voltage = 0.0

# Data storage (for plotting)
times = []
currents = []
voltages = []


# -------------------------
# Worker Thread
# -------------------------

def measurement_worker():
    start_time = time.time()

    while not stop_event.is_set():

        with lock:
            v = voltage

        current = v * 0.5 + random.uniform(-0.01, 0.01)
        t = time.time() - start_time

        data_queue.put((t, v, current))

        time.sleep(0.5)


# -------------------------
# Start Worker
# -------------------------

worker = threading.Thread(target=measurement_worker)
worker.start()


# -------------------------
# Plot Setup
# -------------------------

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [])
ax.set_xlabel("Time (s)")
ax.set_ylabel("Current (A)")
ax.grid(True)

print("Press:")
print("  u → increase voltage")
print("  d → decrease voltage")
print("  q → quit")


# -------------------------
# Key Press Handler
# -------------------------

def on_key(event):
    global voltage

    if event.key == 'u':
        with lock:
            voltage += 0.5
        print(f"Voltage = {voltage}")

    elif event.key == 'd':
        with lock:
            voltage -= 0.5
        print(f"Voltage = {voltage}")

    elif event.key == 'q':
        stop_event.set()

fig.canvas.mpl_connect('key_press_event', on_key)


# -------------------------
# Main Loop (Plot + Queue)
# -------------------------

while not stop_event.is_set():

    # Process new measurement data
    while not data_queue.empty():
        t, v, i = data_queue.get()
        times.append(t)
        currents.append(i)
        voltages.append(v)

    # Update plot
    line.set_data(times, currents)
    ax.relim()
    ax.autoscale_view()

    plt.pause(0.05)

# Cleanup
worker.join()
plt.close()

print("Program finished.")
