import pyvisa
import csv
import time

# ---------- CONFIG ----------
FILENAME = "buffered_measurements.csv"

DRAIN_VOLTAGE = 1.0
GATE_HIGH = 1.0
GATE_LOW = -1.0

DT = 0.01            # sampling interval (s)
PULSE_WIDTH = 1.0
TOTAL_CYCLES = 5

# ---------- VISA ----------
rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.timeout = 20000
k.read_termination = "\n"
k.write_termination = "\n"

try:
    print("Initializing instrument...")

    # ---------- TSP PROGRAM ----------
    tsp = f"""
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
    timebuffer.clear()

    dt = {DT}
    np = math.floor({PULSE_WIDTH} / dt)

    t0 = timer.s()

    for c = 1, {TOTAL_CYCLES} do
        for _, vg in ipairs({{{GATE_HIGH}, {GATE_LOW}}}) do
            smub.source.levelv = vg

            for i = 1, np do
                smua.measure.i(smua.nvbuffer1)
                smub.measure.i(smub.nvbuffer1)
                timebuffer.append(timer.s() - t0)
                delay(dt)
            end
        end
    end

    smua.source.levelv = 0
    smub.source.levelv = 0
    """

    k.write(tsp)

    print("Running buffered measurement...")
    time.sleep(TOTAL_CYCLES * 2 * PULSE_WIDTH + 1)

    # ---------- READ BACK ----------
    print("Downloading data...")

    t = k.query("printbuffer(1, timebuffer.n, timebuffer)").split(',')
    idrain = k.query("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)").split(',')
    igate = k.query("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1.readings)").split(',')

    # ---------- SAVE CSV ----------
    with open(FILENAME, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time_s", "I_Drain_A", "I_Gate_A"])

        for row in zip(t, idrain, igate):
            writer.writerow(row)

    print(f"Saved {len(t)} points to {FILENAME}")

finally:
    print("Shutting down outputs.")
    k.write("smua.source.output = smua.OUTPUT_OFF")
    k.write("smub.source.output = smub.OUTPUT_OFF")
    k.close()
