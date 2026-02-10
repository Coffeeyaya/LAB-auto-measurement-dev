import pyvisa
import time
import csv

# ---------- CONFIG ----------
FILENAME = "keithley_scpi_measurements.csv"

DRAIN_VOLTAGE = 1.0   # V
GATE_HIGH = 1.0       # V
GATE_LOW = -1.0       # V
PULSE_WIDTH = 1.0     # seconds per pulse
TOTAL_CYCLES = 5
DT = 0.01             # sample interval in seconds

# ---------- CONNECT TO GPIB ----------
rm = pyvisa.ResourceManager()
keithley = rm.open_resource("GPIB0::26::INSTR")  # adjust your GPIB address
keithley.write_termination = "\n"
keithley.read_termination = "\n"
keithley.timeout = 10000

# ---------- RESET SMUs ----------
keithley.write("smua.reset()")
keithley.write("smub.reset()")

# Set drain voltage
keithley.write(f"smua.source.func = smua.OUTPUT_DCVOLTS")
keithley.write(f"smua.source.levelv = {DRAIN_VOLTAGE}")
keithley.write("smua.source.output = smua.OUTPUT_ON")

# Set initial gate voltage
keithley.write(f"smub.source.func = smub.OUTPUT_DCVOLTS")
keithley.write(f"smub.source.levelv = {GATE_LOW}")
keithley.write("smub.source.output = smub.OUTPUT_ON")

# ---------- OPEN CSV ----------
with open(FILENAME, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Time_s", "V_Gate", "I_Drain_A", "I_Gate_A"])
    
    start_time = time.time()
    
    # ---------- PULSED MEASUREMENT LOOP ----------
    for cycle in range(TOTAL_CYCLES):
        for gate_voltage in [GATE_HIGH, GATE_LOW]:
            keithley.write(f"smub.source.levelv = {gate_voltage}")
            step_start = time.time()
            
            while (time.time() - step_start) < PULSE_WIDTH:
                t_now = time.time() - start_time
                try:
                    # Query currents directly over SCPI
                    raw = keithley.query("print(smua.measure.i(), smub.measure.i())")
                    vals = raw.strip().split()
                    idrain, igate = vals[0], vals[1]
                    
                    writer.writerow([t_now, gate_voltage, idrain, igate])
                    f.flush()
                    
                except Exception:
                    pass  # ignore occasional read errors

# ---------- TURN OFF OUTPUTS ----------
keithley.write("smua.source.output = smua.OUTPUT_OFF")
keithley.write("smub.source.output = smub.OUTPUT_OFF")

keithley.close()
print(f"SCPI measurement complete. Data saved to {FILENAME}.")
