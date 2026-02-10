import pyvisa
import time
import csv

# ---------- CONFIG ----------
FILENAME = "keithley_scpi_buffer.csv"

DRAIN_VOLTAGE = 1.0
GATE_HIGH = 1.0
GATE_LOW = -1.0
PULSE_WIDTH = 1.0    # seconds per pulse
TOTAL_CYCLES = 5
DT = 0.01            # seconds per sample

# ---------- CONNECT ----------
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("GPIB0::26::INSTR")
keithley.write_termination = "\n"
keithley.read_termination = "\n"
keithley.timeout = 20000

# ---------- RESET SMUs ----------
keithley.write("smua.reset()")
keithley.write("smub.reset()")

# ---------- CONFIGURE SMUA (Drain) ----------
keithley.write("smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
keithley.write("smua.source.output = smua.OUTPUT_ON")
keithley.write("smua.nvbuffer1.clear()")
keithley.write("smua.nvbuffer1.appendmode = 1")
keithley.write("smua.nvbuffer1.timestamps = 1")

# ---------- CONFIGURE SMUB (Gate) ----------
keithley.write("smub.source.func = smub.OUTPUT_DCVOLTS")
keithley.write(f"smub.source.levelv = {GATE_LOW}")
keithley.write("smub.source.output = smub.OUTPUT_ON")
keithley.write("smub.nvbuffer1.clear()")
keithley.write("smub.nvbuffer1.appendmode = 1")
keithley.write("smub.nvbuffer1.timestamps = 1")

# ---------- PULSED MEASUREMENT ----------
for cycle in range(TOTAL_CYCLES):
    for gate_voltage in [GATE_HIGH, GATE_LOW]:
        keithley.write(f"smub.source.levelv = {gate_voltage}")
        npts = int(PULSE_WIDTH / DT)
        for _ in range(npts):
            keithley.write("smua.measure.i(smua.nvbuffer1)")
            keithley.write("smub.measure.i(smub.nvbuffer1)")
            keithley.write(f"delay({DT})")

# ---------- DOWNLOAD BUFFERS ----------
print("Downloading buffers...")
timestamps = keithley.query("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.timestamps)").split(',')
idrain = keithley.query("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)").split(',')
igate = keithley.query("printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1.readings)").split(',')

# ---------- SAVE TO CSV ----------
with open(FILENAME, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Time_s", "I_Drain_A", "I_Gate_A"])
    for row in zip(timestamps, idrain, igate):
        writer.writerow(row)

# ---------- TURN OFF OUTPUTS ----------
keithley.write("smua.source.output = smua.OUTPUT_OFF")
keithley.write("smub.source.output = smub.OUTPUT_OFF")
keithley.close()

print(f"Measurement complete. Data saved to {FILENAME}")
