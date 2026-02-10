import pyvisa
import time
import csv

# ---------- CONFIG ----------
FILENAME = "keithley_measurements.csv"

DRAIN_VOLTAGE = 1.0   # V
GATE_HIGH = 1.0       # V
GATE_LOW = -1.0       # V
PULSE_WIDTH = 1.0     # seconds
TOTAL_CYCLES = 5
DT = 0.01             # sample interval in seconds

# ---------- CONNECT ----------
rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")  # adjust your address
k.write_termination = "\n"
k.read_termination = "\n"
k.timeout = 30000  # 30 seconds for buffered operations

# ---------- STEP 1: HARD RESET ----------
print("Resetting instrument...")
k.write("abort")
time.sleep(0.2)
k.write("reset()")
time.sleep(5)  # wait for TSP engine to initialize

# ---------- STEP 2: LOAD TSP SCRIPT LINE-BY-LINE ----------
print("Loading TSP script...")
tsp_lines = [
    "loadscript pulse_measure",
    "function run_pulse(vds,vgh,vgl,dt,pulse_width,cycles)",
    "smua.reset()",
    "smub.reset()",
    "smua.source.func = smua.OUTPUT_DCVOLTS",
    "smub.source.func = smub.OUTPUT_DCVOLTS",
    "smua.source.limiti = 0.01",
    "smub.source.limiti = 0.001",
    "smua.measure.nplc = 0.01",
    "smub.measure.nplc = 0.01",
    "smua.source.levelv = vds",
    "smua.source.output = smua.OUTPUT_ON",
    "smub.source.output = smub.OUTPUT_ON",
    "smua.nvbuffer1.clear()",
    "smub.nvbuffer1.clear()",
    "smua.nvbuffer1.timestamps = 1",
    "smub.nvbuffer1.timestamps = 1",
    "npts = math.floor(pulse_width/dt)",
    "for c = 1, cycles do",
    "smub.source.levelv = vgh",
    "for i = 1, npts do",
    "smua.measure.i(smua.nvbuffer1)",
    "smub.measure.i(smub.nvbuffer1)",
    "delay(dt)",
    "end",
    "smub.source.levelv = vgl",
    "for i = 1, npts do",
    "smua.measure.i(smua.nvbuffer1)",
    "smub.measure.i(smub.nvbuffer1)",
    "delay(dt)",
    "end",
    "end",
    "smua.source.levelv = 0",
    "smub.source.levelv = 0",
    "end",
    "endscript"
]

# Load the script safely with a short delay per line
for line in tsp_lines:
    k.write(line)
    time.sleep(0.05)  # 50 ms per line

# Small delay after endscript to ensure registration
time.sleep(1)

# ---------- STEP 3: RUN MEASUREMENT ----------
print("Running measurement...")
k.write(f"pulse_measure.run_pulse({DRAIN_VOLTAGE},{GATE_HIGH},{GATE_LOW},{DT},{PULSE_WIDTH},{TOTAL_CYCLES})")

# Wait long enough for the measurement to finish
total_time = TOTAL_CYCLES * 2 * PULSE_WIDTH + 2  # 2-second buffer
time.sleep(total_time)

# ---------- STEP 4: DOWNLOAD BUFFERS ----------
print("Downloading buffer data...")
t = k.query("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.timestamps)").split(',')
idrain = k.query("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)").split(',')
igate = k.query("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1.readings)").split(',')

# ---------- STEP 5: SAVE TO CSV ----------
print(f"Saving data to {FILENAME}...")
with open(FILENAME, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Time_s", "I_Drain_A", "I_Gate_A"])
    for row in zip(t, idrain, igate):
        writer.writerow(row)

# ---------- STEP 6: TURN OFF OUTPUTS ----------
print("Turning outputs OFF...")
k.write("smua.source.output = smua.OUTPUT_OFF")
k.write("smub.source.output = smub.OUTPUT_OFF")

k.close()
print("Done. Measurement complete and saved.")
