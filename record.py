import pyvisa
import csv
import time
import textwrap

# ---------- CONFIG ----------
FILENAME = "buffered_measurements.csv"

DRAIN_VOLTAGE = 1.0
GATE_HIGH = 1.0
GATE_LOW = -1.0

DT = 0.01
PULSE_WIDTH = 1.0
TOTAL_CYCLES = 5

# ---------- VISA ----------
rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.timeout = 30000
k.read_termination = "\n"
k.write_termination = "\n"

try:
    print("Initializing instrument...")

    tsp = textwrap.dedent(f"""
abort
errorqueue.clear()

smua.reset()
smub.reset()

smua.source.func = smua.OUTPUT_DCVOLTS
smub.source.func = smub.OUTPUT_DCVOLTS

smua.source.limiti = 0.01
smub.source.limiti = 0.001

smua.measure.nplc = 0.01
smub.measure.nplc = 0.01

smua.source.levelv = {DRAIN_VOLTAGE}
smua.source.output = smua.OUTPUT_ON
smub.source.output = smub.OUTPUT_ON

smua.nvbuffer1.clear()
smub.nvbuffer1.clear()

smua.nvbuffer1.timestamps = 1
smub.nvbuffer1.timestamps = 1

dt_s = {DT}
npts = math.floor({PULSE_WIDTH} / dt_s)

for c = 1, {TOTAL_CYCLES} do

    smub.source.levelv = {GATE_HIGH}
    for i = 1, npts do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
        delay(dt_s)
    end

    smub.source.levelv = {GATE_LOW}
    for i = 1, npts do
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
        delay(dt_s)
    end

end

smua.source.levelv = 0
smub.source.levelv = 0
""")

    k.write(tsp)

    total_time = TOTAL_CYCLES * 2 * PULSE_WIDTH + 1
    print(f"Running acquisition ({total_time:.1f} s)...")
    time.sleep(total_time)

    print("Downloading buffers...")

    t = k.query(
        "printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.timestamps)"
    ).split(',')

    idrain = k.query(
        "printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)"
    ).split(',')

    igate = k.query(
        "printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1.readings)"
    ).split(',')

    with open(FILENAME, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time_s", "I_Drain_A", "I_Gate_A"])
        for row in zip(t, idrain, igate):
            writer.writerow(row)

    print(f"Saved {len(t)} points to {FILENAME}")

finally:
    print("Turning outputs OFF.")
    k.write("smua.source.output = smua.OUTPUT_OFF")
    k.write("smub.source.output = smub.OUTPUT_OFF")
    k.close()