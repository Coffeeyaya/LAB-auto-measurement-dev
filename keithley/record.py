import pyvisa
import time
import csv

# ---------------- CONFIG ----------------
DRAIN_VOLTAGE = 1.0
VG_HIGH = 1.0
VG_LOW = -1.0
VG_PERIOD = 10.0        # seconds per level
TOTAL_TIME = 60.0       # total experiment time (s)

CSV_FILE = "data.csv"
# ---------------------------------------

rm = pyvisa.ResourceManager()
keithley = rm.open_resource("USB0::0x05E6::0x2636::4407529::INSTR")  # your USB address

keithley.timeout = 10000
keithley.write_termination = "\n"
keithley.read_termination = "\n"

try:
    # ---------- INITIALIZE ----------
    keithley.write("abort")
    keithley.write("errorqueue.clear()")

    keithley.write("smua.reset()")
    keithley.write("smub.reset()")

    # Drain bias
    keithley.write(f"smua.source.func = smua.OUTPUT_DCVOLTS")
    keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
    keithley.write("smua.source.output = smua.OUTPUT_ON")

    # Gate bias
    keithley.write("smub.source.func = smub.OUTPUT_DCVOLTS")
    keithley.write(f"smub.source.levelv = {VG_HIGH}")
    keithley.write("smub.source.output = smub.OUTPUT_ON")

    # Speed optimizations
    keithley.write("smua.measure.nplc = 0.01")
    keithley.write("smub.measure.nplc = 0.01")

    keithley.write("smua.measure.autorangei = smua.AUTORANGE_ON")
    keithley.write("smub.measure.autorangei = smub.AUTORANGE_ON")

    print("Measurement started")

    data = []
    t0 = time.time()
    next_switch = t0 + VG_PERIOD
    vg = VG_HIGH

    # ---------- MAIN LOOP ----------
    while (time.time() - t0) < TOTAL_TIME:
        now = time.time()
        print(now)
        # Toggle gate every 10 s
        if now >= next_switch:
            vg = VG_LOW if vg == VG_HIGH else VG_HIGH
            keithley.write(f"smub.source.levelv = {vg}")
            next_switch += VG_PERIOD
            print(f"Gate switched to {vg:+.1f} V")

        # Measure currents
        raw = keithley.query(
            "print(smua.measure.i(), smub.measure.i())"
        ).strip().split()

        t_rel = now - t0
        idrain = float(raw[0])
        igate = float(raw[1])

        data.append((t_rel, vg, idrain, igate))

    print("Measurement finished")

finally:
    # ---------- CLEANUP ----------
    keithley.write("smua.source.levelv = 0")
    keithley.write("smub.source.levelv = 0")
    keithley.write("smua.source.output = smua.OUTPUT_OFF")
    keithley.write("smub.source.output = smub.OUTPUT_OFF")
    keithley.close()

# ---------- SAVE DATA ----------
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["time_s", "Vg_V", "Id_A", "Ig_A"])
    writer.writerows(data)

print(f"Data saved to {CSV_FILE}")
